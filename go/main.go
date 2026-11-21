// ARGUS-AI Go component: crawler + scheduler + worker pool.
//
// A polite concurrent fetcher skeleton. It reads target URLs (one per
// line) from a file or stdin, fetches them with a bounded worker pool on
// a scheduler tick, respects robots.txt, uses >=1s per-host politeness,
// and appends results as JSONL records to a queue file that the Python
// side ingests. Clearnet public pages only — no auth, no bypass.
package main

import (
	"bufio"
	"encoding/json"
	"flag"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"os"
	"strings"
	"sync"
	"time"
)

const userAgent = "ARGUS-AI GoCrawler/0.5 (personal research; public pages only)"

type Job struct {
	URL string `json:"url"`
}

type Result struct {
	URL       string    `json:"url"`
	Status    int       `json:"status"`
	Bytes     int       `json:"bytes"`
	FetchedAt time.Time `json:"fetched_at"`
	Error     string    `json:"error,omitempty"`
	BodyFile  string    `json:"body_file,omitempty"`
}

type Scheduler struct {
	Jobs chan Job
}

func NewScheduler() *Scheduler { return &Scheduler{Jobs: make(chan Job, 128)} }

func (s *Scheduler) Submit(j Job) { s.Jobs <- j }

type WorkerPool struct {
	Workers int
	Client  *http.Client
	Out     chan Result
	mu      sync.Mutex
	lastHit map[string]time.Time
}

func NewWorkerPool(n int, out chan Result) *WorkerPool {
	return &WorkerPool{
		Workers: n,
		Client:  &http.Client{Timeout: 15 * time.Second},
		Out:     out,
		lastHit: make(map[string]time.Time),
	}
}

func (p *WorkerPool) politeWait(host string) {
	p.mu.Lock()
	defer p.mu.Unlock()
	if t, ok := p.lastHit[host]; ok {
		if d := time.Second - time.Since(t); d > 0 {
			time.Sleep(d)
		}
	}
	p.lastHit[host] = time.Now()
}

func robotsAllow(rawurl string) bool {
	u, err := url.Parse(rawurl)
	if err != nil {
		return false
	}
	resp, err := http.Get(u.Scheme + "://" + u.Host + "/robots.txt")
	if err != nil {
		return false // unreadable robots = skip, same policy as SCOUT
	}
	defer resp.Body.Close()
	body, _ := io.ReadAll(io.LimitReader(resp.Body, 64*1024))
	disallowAll := false
	for _, line := range strings.Split(string(body), "\n") {
		line = strings.TrimSpace(line)
		if strings.HasPrefix(strings.ToLower(line), "disallow:") {
			path := strings.TrimSpace(line[len("disallow:"):])
			if path == "/" {
				disallowAll = true
			}
			if path != "" && strings.HasPrefix(u.Path, path) {
				return false
			}
		}
	}
	return !disallowAll
}

func (p *WorkerPool) Fetch(j Job) Result {
	res := Result{URL: j.URL, FetchedAt: time.Now()}
	u, err := url.Parse(j.URL)
	if err != nil || (u.Scheme != "http" && u.Scheme != "https") {
		res.Error = "only http/https public URLs"
		return res
	}
	if !robotsAllow(j.URL) {
		res.Error = "robots.txt disallows"
		return res
	}
	p.politeWait(u.Host)
	req, err := http.NewRequest("GET", j.URL, nil)
	if err != nil {
		res.Error = err.Error()
		return res
	}
	req.Header.Set("User-Agent", userAgent)
	resp, err := p.Client.Do(req)
	if err != nil {
		res.Error = err.Error()
		return res
	}
	defer resp.Body.Close()
	body, _ := io.ReadAll(io.LimitReader(resp.Body, 200*1024))
	res.Status = resp.StatusCode
	res.Bytes = len(body)
	return res
}

func (p *WorkerPool) Run(s *Scheduler, wg *sync.WaitGroup) {
	for i := 0; i < p.Workers; i++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			for job := range s.Jobs {
				p.Out <- p.Fetch(job)
			}
		}()
	}
}

func main() {
	input := flag.String("input", "", "file with one URL per line (default: stdin)")
	output := flag.String("output", "queue.jsonl", "JSONL queue file for the Python side")
	workers := flag.Int("workers", 4, "worker pool size")
	flag.Parse()

	var scanner *bufio.Scanner
	if *input != "" {
		f, err := os.Open(*input)
		if err != nil {
			fmt.Fprintln(os.Stderr, "open input:", err)
			os.Exit(1)
		}
		defer f.Close()
		scanner = bufio.NewScanner(f)
	} else {
		scanner = bufio.NewScanner(os.Stdin)
	}

	out, err := os.OpenFile(*output, os.O_CREATE|os.O_APPEND|os.O_WRONLY, 0o644)
	if err != nil {
		fmt.Fprintln(os.Stderr, "open output:", err)
		os.Exit(1)
	}
	defer out.Close()

	sched := NewScheduler()
	results := make(chan Result, 128)
	pool := NewWorkerPool(*workers, results)
	var wg sync.WaitGroup
	pool.Run(sched, &wg)

	go func() {
		for scanner.Scan() {
			line := strings.TrimSpace(scanner.Text())
			if line != "" && !strings.HasPrefix(line, "#") {
				sched.Submit(Job{URL: line})
			}
		}
		close(sched.Jobs)
	}()

	go func() { wg.Wait(); close(results) }()

	enc := json.NewEncoder(out)
	n := 0
	for r := range results {
		if err := enc.Encode(r); err == nil {
			n++
			fmt.Printf("fetched %s -> %d (%s)\n", r.URL, r.Status, r.Error)
		}
	}
	fmt.Printf("done: %d results appended to %s\n", n, *output)
}
