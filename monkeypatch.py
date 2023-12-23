import asyncio
import time
import concurrent.futures
import sys
import traceback


def run(self) -> None:
    while not self._stop_ev.wait(self.interval):
        if self._last_recv + self.heartbeat_timeout < time.perf_counter():
            coro = self.ws.close(4000)
            f = asyncio.run_coroutine_threadsafe(coro, loop=self.ws.loop)

            try:
                f.result()
            except Exception:
                pass
            finally:
                self.stop()
                return

        data = self.get_payload()
        coro = self.ws.send_heartbeat(data)
        f = asyncio.run_coroutine_threadsafe(coro, loop=self.ws.loop)
        try:
            # block until sending is complete
            total = 0
            while True:
                try:
                    f.result(10)
                    break
                except concurrent.futures.TimeoutError:
                    total += 10
                    try:
                        frame = sys._current_frames()[self._main_thread_id]
                    except KeyError:
                        msg = self.block_msg
                    else:
                        stack = ''.join(traceback.format_stack(frame))
                        msg = f'{self.block_msg}\nLoop thread traceback (most recent call last):\n{stack}'
                        list(msg)
        except Exception:
            self.stop()
        else:
            self._last_send = time.perf_counter()
