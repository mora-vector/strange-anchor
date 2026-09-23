# Budget behavior and bounded experiments

The compiler emits systemd settings. Their meaning is narrower than a total
job-cost ceiling:

| Declaration | Meaning | Experiment |
| --- | --- | --- |
| cpuPercent | CPU time quota relative to one CPU; throttles, does not kill | Busy units at 10% and 100%; guest-clock usage, cpu.max, and kernel throttle counters |
| memoryMiB | cgroup MemoryMax; swap policy remains with the host | Same 96 MiB allocation at 64 and 192 MiB; OOM result/events versus completion in a guest without swap |
| runtimeMaxSec | Maximum running time per service attempt | 60-second sleep cut off at 3 seconds; short sleep succeeds |
| retries / windowSec | Additional starts after the first within a rate-limit window | Zero/two retries produce one/three exits; extra manual start inside window denied |

All probes run through generated Sandhi units. The test adds an ExecStopPost
observer, preserving SERVICE_RESULT, exit status, and cgroup counters before
systemd can overwrite the final unit result with start-limit-hit. Journals are
retained for timeout, retry, and memory cases. CPU observations come from outside
the workload's control, read in the guest's clock domain. The quota comparison
is not a performance benchmark; it requires observable throttling and bounded
usage, with an actively running higher-quota control.

Start limits are not a lifetime attempt counter. Long attempts can outlast the
window; manual starts count too; reset-failed resets the accounting. RuntimeMaxSec
does not bound stop/preflight time, and retries can multiply runtime. MemoryMax
does not itself prohibit swap. A future total-job budget needs an explicit design;
this checkpoint does not silently change these existing semantics.

The VM has no swap, 1536 MiB RAM, and a 600-second test timeout. Allocation probes
request 96 MiB, and CPU probes terminate after 60 seconds even if the driver loses
control. Run only the unresolved check with `realize.py --check budgets` when
appropriate. Local guest launch was previously denied; CI is the capable builder.

Primary references: [systemd unit rate limits](https://github.com/systemd/systemd/blob/main/man/systemd.unit.xml),
[service runtime/restarts](https://github.com/systemd/systemd/blob/main/man/systemd.service.xml),
[resource controls](https://github.com/systemd/systemd/blob/main/man/systemd.resource-control.xml),
and [kernel cgroup v2 counters](https://docs.kernel.org/admin-guide/cgroup-v2.html).
Actual results concern the pinned NixOS guest, rather than every systemd release.
