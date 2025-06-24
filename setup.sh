#!/bin/bash
RED='\033[0;31m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
NC='\033[0m'
divider() {
echo -e "${YELLOW}---------------------------------------------${NC}"
}
step() {
echo -e "[*] ${YELLOW}$1${NC}"
}
success() {
echo -e "${GREEN}[✓] $1${NC}"
}
fail() {
echo -e "${RED}[✘] $1${NC}"
exit 1
}
divider
step "Cập nhật hệ thống..."
divider
yes | pkg update -y > /dev/null 2>&1 && yes | pkg upgrade -y > /dev/null 2>&1 || fail "Cập nhật gói hệ thống thất bại!"
success "Cập nhật thành công"
divider
step "Cài những gói hệ thống"
divider
pkg install -y python python-pip clang autoconf make cmake automake libtool nmap ninja openssl fftw libopenblas libffi libjpeg-turbo pkg-config libcurl libxml2 libxslt build-essential android-tools > /dev/null 2>&1 || fail "Cài Python thất bại!"
success "Cài gói hệ thống thành công"
divider
step "Cập nhật những gói setuptools"
divider
pip install -q setuptools wheel cython -U > /dev/null 2>&1
success "Cập nhật gói setuptools thành công"
divider
step "Thiết lập những gói Python"
divider
echo -ne "${CYAN}Đang cài lxml==5.4.0...${NC} "
pip uninstall -y lxml > /dev/null 2>&1
CFLAGS="-Wno-error=incompatible-function-pointer-types -O0 -I/data/data/com.termux/files/usr/include" \
LDFLAGS="-L/data/data/com.termux/files/usr/lib" \
PYTHONWARNINGS=ignore pip install -q lxml==5.4.0 > /dev/null 2>&1
[ $? -eq 0 ] && echo -e "${GREEN}✔ Thành công${NC}" || fail "Cài lxml thất bại"
install_pkg() {
local name="$1"
local version="$2"
echo -ne "${CYAN}Đang cài ${name}==${version}...${NC} "
PYTHONWARNINGS=ignore pip install -q "${name}==${version}" > /dev/null 2>&1 || fail "Cài ${name} thất bại"
echo -e "${GREEN}✔ Thành công${NC}"
}
install_pkg "rich" "14.0.0"
install_pkg "numpy" "2.2.6"
install_pkg "pillow" "11.2.1"
install_pkg "adbutils" "2.9.3"
install_pkg "requests" "2.32.4"
install_pkg "uiautomator2" "3.3.3"
install_pkg "cloudscraper" "1.2.71"
divider
step "Kiểm tra module đã cài"
divider
python -c "
import lxml, rich, numpy, PIL, adbutils, requests, uiautomator2, cv2
print('Tất cả module import thành công!')
print('lxml:', lxml.__version__)
print('rich:', rich.__version__)
print('numpy:', numpy.__version__)
print('pillow:', PIL.__version__)
print('adbutils:', adbutils.__version__)
print('requests:', requests.__version__)
print('uiautomator2:', uiautomator2.__version__)
divider
success "Cài đặt hoàn tất! Môi trường Python đã sẵn sàng."