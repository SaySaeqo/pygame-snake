# Not used anymore, but kept for some time in case I will need it again.

import time
import atexit
import logging

count = {}
probes = {}
average_probe_length = 100
average = {}
fps = 60
frame_time = 1/fps
spike_def = 2
critical_def = 4
test_start = None
def log_how_much_time_of_frame(before, what):
    took = time.perf_counter() - before
    if not what in average:
        if what not in count:
            count[what] = 0
            probes[what] = []
        if count[what] < average_probe_length:
            count[what] += 1
            probes[what].append(took)
        if count[what] == average_probe_length:
            probe = probes[what]
            average[what] = sum(probe) / len(probe)
            global test_start
            if not test_start:
                test_start = time.perf_counter()
    elif took/frame_time > 1.0:
        logging.getLogger(__package__).error(f"{what} spiked {took/average[what]:.2f} more than usual. Which is {took/frame_time:.2f} of frame.")
    elif took > average[what]*critical_def:
        logging.getLogger(__package__).warning(f"{what} spiked {took/average[what]:.2f} more than usual. Which is {took/frame_time:.2f} of frame.")
    elif took > average[what]*spike_def:
        logging.getLogger(__package__).info(f"{what} spiked {took/average[what]:.2f} more than usual. Which is {took/frame_time:.2f} of frame.")
    print(f"\r{time.perf_counter() - test_start if test_start else 0:.2f} s", end="")
    return time.perf_counter()

@atexit.register
def log_averages(view = None):
    global test_start
    if test_start:
        view_name = view.__class__.__name__ if view else None
        message = f"END OF VIEW {view_name}:\n--- Averages ---"
        for what, av in average.items():
            message += f"\n{what}: {av/frame_time:.2f} of frame"
        message += "\n--- Minimums ---"
        for what, probe in probes.items():
            message += f"\n{what}: {min(probe)/frame_time:.2f} of frame"
        message += "\n--- Test references ---"
        message += f"\nFps: {fps}"
        message += f"\nAverage probe length: {average_probe_length}"
        message += f"\nTest duration: {time.perf_counter() - test_start:.2f} s"
        message += f"\nSpike criteria: {spike_def} times more than average"
        logging.getLogger(__package__).warning(message)
    average.clear()
    count.clear()
    probes.clear()
    test_start = None