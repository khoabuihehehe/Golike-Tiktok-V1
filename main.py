#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os, re, time, json, shutil
import uiautomator2 as u2
from cloudscraper import create_scraper
from threading import Lock, Thread
from adbutils import AdbClient
from rich.table import Table
from rich.live import Live
from pathlib import Path


class ADB:
    def __init__(self, serial=None):
        self.d = u2.connect(serial) if serial else u2.connect()

    def tap(self, x, y):
        self.d.click(x, y)

    def input_text(self, text, clear=False):
        self.d.send_keys(text, clear)

    def find_xpath(self, xpath):
        e = self.d.xpath(xpath)
        if e.exists:
            return e.all()
        return None

    def find_element(self, **kwargs):
        e = self.d(**kwargs)
        if e.exists:
            return e
        return None

    def click_element(self, **kwargs):
        e = self.find_element(**kwargs)
        if e:
            e.click()
            return True
        return False

    def open_url(self, url):
        self.d.open_url(url)

    def wait_for_element(self, timeout=10.0, **kwargs):
        return self.d(**kwargs).wait(timeout=timeout)

    def wait_for_click(self, timeout=10.0, **kwargs):
        if self.wait_for_element(timeout, **kwargs):
            return self.click_element(**kwargs)
        return False

    def wait_for_input(self, text, clear=False, timeout=10.0, **kwargs):
        if self.wait_for_element(timeout, **kwargs):
            self.click_element(**kwargs)
            self.input_text(text, clear)
            return True
        return False

    def press_key(self, key):
        self.d.press(key)

    def dump_hierarchy(self):
        xml = self.d.dump_hierarchy()
        return xml

    def drag(self, sx, sy, ex, ey, duration=0.1):
        self.d.drag(sx, sy, ex, ey, duration)

    def wait_for_drag_element(self, direction="right", distance=100, duration=0.1, timeout=10.0, **kwargs):
        if self.wait_for_element(timeout, **kwargs):
            element = self.find_element(**kwargs)
            if not element:
                return False
            bounds = element.bounds()
            sx = (bounds['left'] + bounds['right']) // 2
            sy = (bounds['top'] + bounds['bottom']) // 2
            if direction.lower() == "right":
                ex, ey = sx + distance, sy
            elif direction.lower() == "left":
                ex, ey = sx - distance, sy
            elif direction.lower() == "up":
                ex, ey = sx, sy - distance
            else:
                ex, ey = sx, sy + distance
            element.drag_to(ex, ey, duration=duration)
            return True
        return False

    def swipe(self, sx, sy, ex, ey, duration=0.1):
        self.d.swipe(sx, sy, ex, ey, duration)

    def screenshot(self, path=None):
        img = self.d.screenshot()
        if path:
            img.save(path)
        return img

    def back(self):
        self.d.press("back")

    def home(self):
        self.d.press("home")

    def recent(self):
        self.d.press("recent")

    def start_app(self, package, activity=None):
        self.d.app_start(package, activity, wait=True)

    def stop_app(self, package):
        self.d.app_stop(package)

    def clear_app(self, package):
        self.d.app_clear(package)


class GOLIKE:
    def __init__(self):
        self.s = create_scraper(browser={'browser': 'chrome', 'platform': 'android', 'mobile': True, 'desktop': False, 'custom': 'chrome124'})
        self.s.headers = {
            'content-type': 'application/json;charset=utf-8',
            'origin': 'https://app.golike.net',
            't': 'VFZSak1FOVVZM2RPYWxWNlRsRTlQUT09',
            'user-agent': 'Mozilla/5.0 (Android 9; Mobile; SM-N976N) AppleWebKit/537.36 Chrome/124.0.6367.82 Mobile Safari/537.36'
        }
        self.b = "https://gateway.golike.net/api"
        self.af = self.load_auth()

    def load_auth(self):
        af = Path("data/authors.txt")
        af.parent.mkdir(parents=True, exist_ok=True)
        if not af.exists() or not af.read_text():
            auth = input("Nhập AUTH: ")
            af.write_text(auth)
        else:
            auth = af.read_text()
        self.s.headers.update({'authorization': auth})
        return af

    def get_user(self):
        res = self.s.get(f"{self.b}/users/me").json()
        if res.get("status") == 401:
            self.af.unlink()
            raise ValueError("Authorization không chính xác!")
        return res.get("data")

    def get_account(self):
        res = self.s.get(f"{self.b}/tiktok-account").json()
        if res.get("status") != 200:
            error = res.get("error")
            raise ValueError(error)
        return res.get("data")

    def get_job(self, acc_id):
        return self.s.get(
            f"{self.b}/advertising/publishers/tiktok/jobs",
            params={'account_id': acc_id, 'data': 'null'}
        ).json()

    def skip_job(self, ads_id, obj_id, acc_id, job_type):
        self.s.post(f"{self.b}/report/send", json={'description': 'Tôi không muốn làm Job này', 'users_advertising_id': ads_id, 'type': 'ads', 'provider': 'tiktok', 'fb_id': acc_id, 'error_type': 0})
        self.s.post(f"{self.b}/advertising/publishers/tiktok/skip-jobs", json={'ads_id': ads_id, 'object_id': obj_id, 'account_id': acc_id, 'type': job_type})

    def complete_job(self, ads_id, acc_id):
        return self.s.post(
            f"{self.b}/advertising/publishers/tiktok/complete-jobs",
            json={'ads_id': ads_id, 'account_id': acc_id, 'async': True, 'data': None}
        ).json()


class GUI:
    def __init__(self, devices):
        self.share_data = {}
        self.row_id = len(devices)
        self.lock = Lock()

    def create_table(self):
        title = "[yellow]===[/yellow]   [white]Danh sách luồng GOLIKE[/white]   [yellow]===[/yellow]"
        tab = Table(title=title, show_header=True)
        widths = {'STT': 5, 'USER': 15, 'DEVICE': 27, 'TIME': 10, 'DONE': 8, 'SKIP': 8, 'EARN': 8}
        size = shutil.get_terminal_size()
        ter_width = size.columns
        total_width = sum(widths.values())
        padding = len(widths) + 1
        message_width = max(3, ter_width - total_width - padding)
        tab.add_column("[cyan]STT[/cyan]", justify="center", width=widths['STT'])
        tab.add_column("[white]USER[/white]", justify="center", width=widths['USER'])
        tab.add_column("[green]DEVICE[/green]", justify="center", width=widths['DEVICE'])
        tab.add_column("[magenta]TIME[/magenta]", justify="center", width=widths['TIME'])
        tab.add_column("[bright_green]DONE[/bright_green]", justify="center", width=widths['DONE'])
        tab.add_column("[yellow]SKIP[/yellow]", justify="center", width=widths['SKIP'])
        tab.add_column("[bright_blue]EARN[/bright_blue]", justify="center", width=widths['EARN'])
        tab.add_column("[white]MESSAGE[/white]", justify="center", width=message_width)
        return tab

    def update_table(self, live):
        while True:
            tab = self.create_table()
            with self.lock:
                now = time.strftime("%H:%M:%S")
                for i in range(1, self.row_id + 1):
                    if i in self.share_data.keys():
                        row = self.share_data[i]
                        stt = f"[bold cyan]{row['STT']}[/bold cyan]"
                        user = f"[bold white]{row['USER']}[/bold white]"
                        device = f"[green]{row['DEVICE']}[/green]"
                        time_str = f"[bright_magenta]{now}[/bright_magenta]"
                        done = f"[bold bright_green]{row['DONE']}[/bold bright_green]"
                        skip = f"[bold yellow]{row['SKIP']}[/bold yellow]"
                        earn = f"[bold bright_blue]{row['EARN']}[/bold bright_blue]"
                        message = row['MESSAGE']
                        tab.add_row(stt, user, device, time_str, done, skip, earn, message, end_section=True)
            time.sleep(1)
            live.update(tab)

    def update_row(self, row, user, serial, done, skip, earn, mess):
        with self.lock:
            self.share_data[row] = {'STT': str(row), 'USER': str(user), 'DEVICE': str(serial),
                'DONE': str(done), 'SKIP': str(skip), 'EARN': str(earn), 'MESSAGE': str(mess)
            }


class TIKTOK:
    def __init__(self):
        self.s = create_scraper(browser={'browser': 'chrome', 'custom': 'chrome124'})
        self.s.headers = {
            'accept-language': 'en-US;q=0.6,en;q=0.5',
            'upgrade-insecure-requests': '1',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.6367.82 Safari/537.36'
        }
        self.b = "https://www.tiktok.com/"

    def profile(self, user_id):
        try:
            res = self.s.get(f"{self.b}@{user_id}")
            res.raise_for_status()
            match = re.search(r'"user":\s*({(?:[^{}]|{[^{}]*})*})', res.text)
            if not match:
                return {'status': False, 'error': 'Dell tìm thấy tài khoản'}
            data = json.loads(match.group(1))
            if data.get("privateAccount"):
                return {'status': False, 'error': 'Dính riêng tư'}
            useruid = data["id"]
            uniqueid = data["uniqueId"]
            return {'status': True, 'web_tt': f'{self.b}@{uniqueid}', 'dl_ttt': f'tiktok://user/profile/{useruid}?refer=web&gd_label=click_wap_download_follow&type=need_follow&needlaunchlog=1'}
        except Exception as e:
            return {'status': False, 'error': str(e)}


def run(gl: GOLIKE, gui: GUI, row, serial):
    os.system('cls' if os.name == 'nt' else 'clear')
    done = skip = earn = fail = 0

    gui.update_row(row, "null", serial, done, skip, earn,
                "[bold bright_green]Đang khởi động máy chủ.[/bold bright_green]")

    adb = ADB(serial)
    tiktok = TIKTOK()
    accounts = gl.get_account()

    gui.update_row(row, "null", serial, done, skip, earn,
                "[bold bright_green]Đang mở ứng dụng TikTok.[/bold bright_green]")
    adb.start_app("com.ss.android.ugc.trill", "com.ss.android.ugc.aweme.splash.SplashActivity")

    gui.update_row(row, "null", serial, done, skip, earn,
                "[bold bright_green]Đang chuyển qua trang Profile.[/bold bright_green]")
    adb.wait_for_click(500, text="Hồ sơ")

    user = next(e.text.lstrip("@") for e in adb.find_xpath("//*") if e.text and e.text.startswith("@"))
    acc_id = next((a['id'] for a in accounts if a['unique_username'] == user), None)

    if not acc_id:
        gui.update_row(row, user, serial, done, skip, earn,
                    f"[bold bright_green]Tài khoản [bold bright_yellow]['{user}'][/bold bright_yellow] chưa thêm vào GOLIKE.[/bold bright_green]")
        return

    gui.update_row(row, user, serial, done, skip, earn,
                f"[bold bright_green]Lấy tài khoản [bold bright_yellow]['{user}'][/bold bright_yellow] thành công.[/bold bright_green]")

    while True:
        if fail >= 10:
            gui.update_row(row, user, serial, done, skip, earn,
                        f"[bold bright_green]Tài khoản [bold bright_yellow]['{user}'][/bold bright_yellow] gặp sự cố.[/bold bright_green]")
            break

        gui.update_row(row, user, serial, done, skip, earn,
                    "[bold bright_green]Đang tìm kiếm nhiệm vụ.[/bold bright_green]")
        job = gl.get_job(acc_id)

        if job['status'] != 200:
            for i in range(10, -1, -1):
                gui.update_row(row, user, serial, done, skip, earn,
                            f"[bold bright_white][[bold bright_yellow]{i}[/bold bright_yellow]][/bold bright_white] "
                            f"[bold bright_green]Không tìm thấy nhiệm vụ.[/bold bright_green]")
                time.sleep(1)
            continue

        job_id = job['data']['id']
        obj_id = job['data']['object_id']
        job_type = job['data']['type']

        profile = tiktok.profile(obj_id)

        if job_type not in ["like", "follow"]:
            skip += 1
            gui.update_row(row, user, serial, done, skip, earn,
                        f"[bold bright_green]Bỏ qua nhiệm vụ [bold bright_yellow]['{job_type}'][/bold bright_yellow].[/bold bright_green]")
            gl.skip_job(job_id, obj_id, acc_id, job_type)
            continue

        if not profile['status']:
            skip += 1
            gui.update_row(row, user, serial, done, skip, earn,
                        "[bold bright_green]Nhiệm vụ không đạt tiêu chuẩn.[/bold bright_green]")
            gl.skip_job(job_id, obj_id, acc_id, job_type)
            continue

        url = profile['dl_ttt']
        adb.open_url(url)

        btn_label = "Thích" if job_type == "like" else "Follow"
        gui.update_row(row, user, serial, done, skip, earn,
                    f"[bold bright_green]Đang nhấn nút [bold bright_white][[bold bright_yellow]'{job_type.upper()}'[/bold bright_yellow]][/bold bright_white].[/bold bright_green]")
        adb.wait_for_click(description="Thích") if job_type == "like" else adb.wait_for_click(text="Follow")

        for i in range(10, -1, -1):
            gui.update_row(row, user, serial, done, skip, earn,
                        f"[bold bright_white][[bold bright_yellow]{i}[/bold bright_yellow]][/bold bright_white] "
                        "[bold bright_green]Đang nhận phần thưởng.[/bold bright_green]")
            time.sleep(1)

        adb.back()

        for attempt in range(1, 4):
            try:
                res = gl.complete_job(job_id, acc_id)
                if res['status'] == 200:
                    fail = 0
                    done += 1
                    earn += res['data']['prices']
                    gui.update_row(row, user, serial, done, skip, earn,
                                f"[bold bright_white][[bold bright_yellow]SUCCESS[/bold bright_yellow]][/bold bright_white] "
                                f"[bold bright_green]Nhận +[bold bright_yellow]{res['data']['prices']}[/bold bright_yellow].[/bold bright_green]")
                    break
                else:
                    for i in range(5, -1, -1):
                        gui.update_row(row, user, serial, done, skip, earn,
                                    f"[bold bright_white][[bold bright_yellow]{i}[/bold bright_yellow]][/bold bright_white] "
                                    f"[bold bright_green]Thất bại lần {attempt}.[/bold bright_green]")
                        time.sleep(1)
            except:
                gui.update_row(row, user, serial, done, skip, earn,
                            "[bold bright_white][[bold bright_yellow]FAILURE[/bold bright_yellow]][/bold bright_white] "
                            "[bold bright_green]Lỗi không rõ.[/bold bright_green]")
        else:
            skip += 1
            fail += 1
            gui.update_row(row, user, serial, done, skip, earn,
                        "[bold bright_white][[bold bright_yellow]FAILURE[/bold bright_yellow]][/bold bright_white] "
                        "[bold bright_green]Nhận thưởng thất bại.[/bold bright_green]")
            gl.skip_job(job_id, obj_id, acc_id, job_type)

def main():
    try:
        golike = GOLIKE()
        client = AdbClient()
        devices = client.device_list()
        gui = GUI(devices)

        for row, device in enumerate(devices, 1):
            t = Thread(target=run, args=(golike, gui, row, device.serial), daemon=True)
            t.start()

        with Live(gui.create_table(), refresh_per_second=20) as live:
            gui.update_table(live)

    except ValueError as e:
        print(f"Lỗi: {str(e)}")
    except KeyboardInterrupt:
        print("Dừng bởi người dùng.")
    except Exception as e:
        print(f"Lỗi không xác định: {str(e)}.")


if __name__ == "__main__":
    main()
