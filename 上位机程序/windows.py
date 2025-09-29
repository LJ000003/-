#!/usr/bin/env python3
# windows.py
"""
串口游戏助手（带日志、单张/对/三条比较、五局三胜）
新增要求：第5字节为 0x00 -> 继续，0x01 -> 结束并根据当前比分判断胜者
依赖:
    pip install pyqt5 pyserial
运行:
    python windows.py
"""

import sys      
import datetime #日志条目
from PyQt5 import QtCore, QtWidgets, QtGui
import serial
import serial.tools.list_ports
from serial import SerialException

# ========== 配置与映射 ==========
CARD_TEXT = {
    0x00: "-",
    0x01: "A",
    0x02: "2",
    0x03: "3",
    0x04: "4",
    0x05: "5",
    0x06: "6",
    0x07: "7",
    0x08: "8",
    0x09: "9",
    0x0A: "10",
    0x0B: "J",
    0x0C: "Q",
    0x0D: "K",
}

# 斗地主式比较顺序：3 最小 ... K A 2 最大
RANK_ORDER = {
    0x03: 1,
    0x04: 2,
    0x05: 3,
    0x06: 4,
    0x07: 5,
    0x08: 6,
    0x09: 7,
    0x0A: 8,
    0x0B: 9,
    0x0C: 10,
    0x0D: 11,
    0x01: 12,
    0x02: 13,
}

def card_display(b):
    return CARD_TEXT.get(b, "?")

def card_rank(b):
    return RANK_ORDER.get(b, -999)

# ========== 串口读取线程 ==========
class SerialReaderThread(QtCore.QThread):
    packet_received = QtCore.pyqtSignal(bytes)

    def __init__(self, ser: serial.Serial = None, parent=None):
        super().__init__(parent)
        self.ser = ser
        self._running = False
        self._buffer = bytearray()

    def set_serial(self, ser: serial.Serial):
        self.ser = ser

    def start_reading(self):
        self._running = True
        if not self.isRunning():
            self.start()

    def stop_reading(self):
        self._running = False
        self.wait(300)

    def run(self):
        while self._running:
            try:
                if not self.ser or not getattr(self.ser, "is_open", False):
                    self.msleep(100)
                    continue
                data = self.ser.read(self.ser.in_waiting or 1)
                if data:
                    self._buffer.extend(data)
                    while len(self._buffer) >= 5:
                        pkt = bytes(self._buffer[:5])
                        del self._buffer[:5]
                        self.packet_received.emit(pkt)
                else:
                    self.msleep(20)
            except Exception as e:
                print("SerialReaderThread error:", e)
                self.msleep(200)

# ========== 主窗口 ==========
class GameWindow(QtWidgets.QWidget):
    DEFAULT_BAUDRATE = 2400
    MATCH_TARGET = 3  # 五局三胜：先得到 3 分者获胜

    def __init__(self):
        super().__init__()
        self.setWindowTitle("双人扑克游戏助手")
        self.resize(1000, 700)

        self.ser = None
        self.reader = SerialReaderThread()
        self.reader.packet_received.connect(self.on_packet_received)

        # 局分
        self.score_player1 = 0
        self.score_player2 = 0

        # 上一手记录
        self.last_cards = None
        self.last_type = None
        self.last_rank = None

        self.init_ui()

    def init_ui(self):
        main_layout = QtWidgets.QVBoxLayout(self)

        # 顶部串口行
        port_layout = QtWidgets.QHBoxLayout()
        self.port_cb = QtWidgets.QComboBox()
        self.refresh_ports()
        refresh_btn = QtWidgets.QPushButton("刷新端口")
        refresh_btn.clicked.connect(self.refresh_ports)
        open_tip = QtWidgets.QLabel(f"(波特率固定: {self.DEFAULT_BAUDRATE})")
        self.open_btn = QtWidgets.QPushButton("打开串口")
        self.open_btn.clicked.connect(self.toggle_port)

        port_layout.addWidget(QtWidgets.QLabel("端口:"))
        port_layout.addWidget(self.port_cb)
        port_layout.addWidget(refresh_btn)
        port_layout.addWidget(open_tip)
        port_layout.addWidget(self.open_btn)
        port_layout.addStretch()
        main_layout.addLayout(port_layout)

        # 中部：得分与牌（左3=上次 / 右3=本次）
        display_group = QtWidgets.QGroupBox()
        display_layout = QtWidgets.QGridLayout(display_group)
        display_layout.setVerticalSpacing(12)
        display_layout.setHorizontalSpacing(12)

        player_font = "font-size:28px; font-weight:bold;"
        lbl_font = "font-size:16px;"

        display_layout.addWidget(QtWidgets.QLabel("一号选手得分:"), 0, 0)
        self.p1_label = QtWidgets.QLabel(str(self.score_player1))
        self.p1_label.setStyleSheet(player_font + " color: blue;")
        display_layout.addWidget(self.p1_label, 0, 1)

        display_layout.addWidget(QtWidgets.QLabel("二号选手得分:"), 0, 2)
        self.p2_label = QtWidgets.QLabel(str(self.score_player2))
        self.p2_label.setStyleSheet(player_font + " color: red;")
        display_layout.addWidget(self.p2_label, 0, 3)

        display_layout.addWidget(QtWidgets.QLabel("牌（左3=上次 / 右3=本次）:"), 1, 0)
        card_hbox = QtWidgets.QHBoxLayout()
        self.card_labels = []
        for i in range(6):
            lbl = QtWidgets.QLabel("-")
            lbl.setFixedSize(130, 90)
            lbl.setAlignment(QtCore.Qt.AlignCenter)
            lbl.setStyleSheet("border:2px solid gray; font-size:28px; background:#FFF;")
            card_hbox.addWidget(lbl)
            self.card_labels.append(lbl)
        display_layout.addLayout(card_hbox, 1, 1, 1, 3)

        display_layout.addWidget(QtWidgets.QLabel("游戏状态:"), 2, 0)
        self.state_label = QtWidgets.QLabel("未开始")
        self.state_label.setStyleSheet(lbl_font + " font-weight:bold;")
        display_layout.addWidget(self.state_label, 2, 1)

        self.reset_btn = QtWidgets.QPushButton("重新开始 (清零)")
        self.reset_btn.setFixedWidth(180)
        self.reset_btn.clicked.connect(self.reset_game)
        display_layout.addWidget(self.reset_btn, 2, 3)

        main_layout.addWidget(display_group)

        # 底部：日志区
        log_group = QtWidgets.QGroupBox("接收日志")
        log_layout = QtWidgets.QVBoxLayout(log_group)
        self.log_edit = QtWidgets.QTextEdit()
        self.log_edit.setReadOnly(True)
        self.log_edit.setMinimumHeight(220)
        log_buttons_layout = QtWidgets.QHBoxLayout()
        self.clear_log_btn = QtWidgets.QPushButton("清除日志")
        self.clear_log_btn.clicked.connect(self.clear_log)
        self.sim_btn = QtWidgets.QPushButton("模拟发送测试包")
        self.sim_btn.clicked.connect(self.simulate_scenarios)

        log_buttons_layout.addWidget(self.clear_log_btn)
        log_buttons_layout.addWidget(self.sim_btn)
        log_buttons_layout.addStretch()

        log_layout.addLayout(log_buttons_layout)
        log_layout.addWidget(self.log_edit)

        main_layout.addWidget(log_group)
    #串口刷新
    def refresh_ports(self):
        cur = self.port_cb.currentText() if self.port_cb.count() > 0 else ""
        self.port_cb.clear()
        ports = serial.tools.list_ports.comports()
        for p in ports:
            self.port_cb.addItem(p.device)
        if cur:
            idx = self.port_cb.findText(cur)
            if idx >= 0:
                self.port_cb.setCurrentIndex(idx)

    def toggle_port(self):
        if self.ser and getattr(self.ser, "is_open", False):
            self.close_port()
        else:
            self.open_port()

    def open_port(self):
        if self.port_cb.count() == 0:
            QtWidgets.QMessageBox.warning(self, "错误", "未检测到任何串口设备。请插入设备并点击刷新。")
            return
        port = self.port_cb.currentText().strip()
        if not port:
            QtWidgets.QMessageBox.warning(self, "错误", "请选择串口。")
            return
        try:
            self.ser = serial.Serial(port=port, baudrate=self.DEFAULT_BAUDRATE, timeout=0.1)
            self.open_btn.setText("关闭串口")
            self.reader.set_serial(self.ser)
            self.reader.start_reading()
            self.append_log(f"打开串口 {port}，波特率 {self.DEFAULT_BAUDRATE}")
        except SerialException as e:
            QtWidgets.QMessageBox.critical(self, "打开串口失败", str(e))
            self.ser = None
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "打开串口异常", str(e))
            self.ser = None

    def close_port(self):
        try:
            if self.reader:
                self.reader.stop_reading()
            if self.ser and getattr(self.ser, "is_open", False):
                self.ser.close()
            self.open_btn.setText("打开串口")
            self.append_log("已关闭串口")
        except Exception as e:
            QtWidgets.QMessageBox.warning(self, "关闭串口出错", str(e))

    # ---------- 日志相关 ----------
    def append_log(self, text: str):
        ts = datetime.datetime.now().strftime("%H:%M:%S.%f")[:-3]
        self.log_edit.append(f"[{ts}] {text}")
        # 自动滚动到底部
        self.log_edit.moveCursor(QtGui.QTextCursor.End)

    def clear_log(self):
        self.log_edit.clear()
        self.append_log("日志已清除")

    # ---------- 牌型分析 ----------
    def analyze_cards(self, cards):
        a, b, c = cards
        if a == 0x00 and b == 0x00 and c == 0x00:
            return 'all_zero', None, None
        cnt = {}
        for i, x in enumerate((a, b, c)):
            if x not in cnt:
                cnt[x] = []
            cnt[x].append(i)
        for k, pos in cnt.items():
            if k != 0x00 and len(pos) == 3:
                return 'triple', k, None
        for k, pos in cnt.items():
            if k != 0x00 and len(pos) == 2:
                return 'pair', k, None
        nonzero = [(i, x) for i, x in enumerate((a, b, c)) if x != 0x00]
        if len(nonzero) == 1:
            idx, val = nonzero[0]
            return 'single', val, idx
        return 'none', None, None

    # ---------- 主处理逻辑 ----------
    def on_packet_received(self, packet: bytes):
        if len(packet) != 5:
            print("收到非5字节包:", packet)
            return

        hex_str = " ".join(f"{b:02X}" for b in packet)
        self.append_log(f"收到原始包: {hex_str}")

        dealer = packet[0]
        cards = [packet[1], packet[2], packet[3]]
        state = packet[4]  # 第五字节：0x00 继续，0x01 结束并比较比分

        # 更新 UI 左侧（last）与右侧（current）
        if self.last_cards:
            for i in range(3):
                self.card_labels[i].setText(card_display(self.last_cards[i]))
        else:
            for i in range(3):
                self.card_labels[i].setText("-")
        for i in range(3):
            self.card_labels[3 + i].setText(card_display(cards[i]))

        # 验证 dealer
        if dealer not in (0x01, 0x02):
            self.append_log(f"未知发牌者: 0x{dealer:02X}，忽略该包")
            return
        dealer_text = "一号" if dealer == 0x01 else "二号"

        # 分析牌型
        ctype, crank, single_pos = self.analyze_cards(cards)
        card_texts = ", ".join(card_display(c) for c in cards)
        cr_text = card_display(crank) if crank is not None else "-"
        self.append_log(f"解析：发牌者={dealer_text}，牌=[{card_texts}]，牌型={ctype}，比较值={cr_text}，state=0x{state:02X}")

        # 如果第五字节为 0x01 -> 结束比赛并根据当前比分判断胜者（立即触发）
        if state == 0x01:
            self.append_log("收到结束标志（第五字节=0x01），根据当前比分判定胜者")
            self._handle_game_end_by_score()
            return

        # state == 0x00 -> 继续，按常规比较流程
        # 优先处理 all_zero 与 none
        if ctype == 'all_zero':
            self.append_log("判定：all_zero（发三张0），对手得分并重置回合")
            self._award_point_and_reset(dealer, reason="发三张0（非法）")
            return

        if ctype == 'none':
            self.append_log("判定：none（全不同），对手得分并重置回合")
            self._award_point_and_reset(dealer, reason="出牌均不同（无重复）")
            return

        # ctype in single/pair/triple
        if self.last_type is None:
            self.last_cards = cards.copy()
            self.last_type = ctype
            self.last_rank = crank
            self.append_log(f"记录为上一手: 类型={ctype}，比较牌={card_display(crank)}，等待对手出牌")
            self.state_label.setText(f"记录上一手: {ctype} of {card_display(crank)}，等待对手出牌")
            return

        # 有上一手
        self.append_log(f"上一手：类型={self.last_type}，比较牌={card_display(self.last_rank)}")
        if self.last_type != ctype:
            self.append_log("判定：类型不一致 -> 对手得分并重置回合")
            self._award_point_and_reset(dealer, reason="类型不一致（需相同类型）")
            return

        last_rank_value = card_rank(self.last_rank)
        curr_rank_value = card_rank(crank)
        self.append_log(f"比较：当前牌值={curr_rank_value}，上一手牌值={last_rank_value}")

        if curr_rank_value > last_rank_value:
            old_last = (self.last_type, self.last_rank)
            self.last_cards = cards.copy()
            self.last_type = ctype
            self.last_rank = crank
            self.append_log(f"合法超越：{card_display(crank)} > {card_display(old_last[1])}，回合继续")
            self.state_label.setText(f"合法超越：{card_display(crank)} > {card_display(old_last[1])}，回合继续")
            return
        else:
            self.append_log("判定：未超越上一手 -> 对手得分并重置回合")
            self._award_point_and_reset(dealer, reason="未超越上一手")
            return

    # ---------- 得分与重置（五局三胜判定） ----------
    def _award_point_and_reset(self, dealer, reason="规则判定"):
        """
        给对手加一分（局分），然后检查是否达到 MATCH_TARGET（3 分）胜利条件。
        若达成 match 胜利，弹窗显示并可选择重新开始（清零）。
        然后重置回合（清空 last_* 与牌 UI）。
        """
        if dealer == 0x01:
            self.score_player2 += 1
            scorer = "二号"
        else:
            self.score_player1 += 1
            scorer = "一号"
        self._update_score_labels()
        # 记录日志
        self.append_log(f"{reason} -> {scorer} 得一分（当前比分：一号 {self.score_player1} - 二号 {self.score_player2}）")

        # 检查五局三胜（先得 MATCH_TARGET 分者获胜）
        if self.score_player1 >= self.MATCH_TARGET or self.score_player2 >= self.MATCH_TARGET:
            if self.score_player1 >= self.MATCH_TARGET:
                winner = "一号选手"
            else:
                winner = "二号选手"
            self.append_log(f"赛局胜出：{winner} 达到 {self.MATCH_TARGET} 分，赛局结束")
            QtCore.QTimer.singleShot(10, lambda: self._show_match_winner_and_reset_dialog(winner))
            # 不立即清空比分（让用户看到最终比分），但仍重置回合牌态
            self.last_cards = None
            self.last_type = None
            self.last_rank = None
            for i in range(6):
                self.card_labels[i].setText("-")
            self.state_label.setText(f"{winner} 获得 {self.MATCH_TARGET} 分，赛局结束")
            return

        # 若未达成赛局胜利，则只重置回合继续下一局
        self.last_cards = None
        self.last_type = None
        self.last_rank = None
        for i in range(6):
            self.card_labels[i].setText("-")
        self.state_label.setText(f"{reason}，{scorer} 得分，回合结束（未达赛局胜利）")

    def _show_match_winner_and_reset_dialog(self, winner_text: str):
        msg = QtWidgets.QMessageBox(self)
        msg.setWindowTitle("赛局结束 - 五局三胜")
        msg.setText(f"{winner_text} 获得 {self.MATCH_TARGET} 分，赛局胜出！")
        msg.setInformativeText(f"最终比分：一号 {self.score_player1} - 二号 {self.score_player2}")
        restart_btn = msg.addButton("重新开始（清零）", QtWidgets.QMessageBox.AcceptRole)
        msg.addButton("关闭", QtWidgets.QMessageBox.RejectRole)
        msg.exec_()
        if msg.clickedButton() == restart_btn:
            self.reset_game()
        else:
            self.append_log("用户选择不重置赛局，比分保持显示；可点击“重新开始(清零)”手动重置。")

    def _handle_game_end_by_score(self):
        """
        当收到第五字节为 0x01 时调用：根据当前比分判断并显示赢家（或平局）。
        不改变比分（由用户决定是否重置）。
        """
        if self.score_player1 > self.score_player2:
            winner = "一号选手获胜！"
        elif self.score_player2 > self.score_player1:
            winner = "二号选手获胜！"
        else:
            winner = "平局！"
        self.append_log(f"收到结束标志 -> {winner}（当前比分：一号 {self.score_player1} - 二号 {self.score_player2}）")
        # 弹窗显示并提供重置选项
        QtCore.QTimer.singleShot(10, lambda: self.show_winner_dialog(winner))

    def show_winner_dialog(self, winner_text: str):
        msg = QtWidgets.QMessageBox(self)
        msg.setWindowTitle("比赛结束")
        msg.setText(winner_text)
        msg.setInformativeText(f"比分：一号 {self.score_player1} - 二号 {self.score_player2}")
        restart_btn = msg.addButton("重新开始（清零）", QtWidgets.QMessageBox.AcceptRole)
        msg.addButton("关闭", QtWidgets.QMessageBox.RejectRole)
        msg.exec_()
        if msg.clickedButton() == restart_btn:
            self.reset_game()

    def _update_score_labels(self):
        self.p1_label.setText(str(self.score_player1))
        self.p2_label.setText(str(self.score_player2))

    def reset_game(self):
        # 完整重置：比分与回合均清零
        self.score_player1 = 0
        self.score_player2 = 0
        self._update_score_labels()
        self.last_cards = None
        self.last_type = None
        self.last_rank = None
        for i in range(6):
            self.card_labels[i].setText("-")
        self.state_label.setText("未开始（已清零）")
        self.append_log("按下重置：比分与回合已清零")

    # ---------- 模拟测试 ----------
    def simulate_scenarios(self):
        tests = []

        def mk_pkt(dealer, c1, c2, c3, state=0x00):
            return bytes([dealer, c1, c2, c3, state])

        # 模拟流程演示，包括第五字节=0x01 的结束包
        tests.append(mk_pkt(0x01, 0x05, 0x00, 0x00, 0x00))  # single(5)
        tests.append(mk_pkt(0x02, 0x07, 0x00, 0x00, 0x00))  # single(7) -> 超越
        tests.append(mk_pkt(0x01, 0x06, 0x06, 0x03, 0x00))  # pair -> 类型不一致 -> 对手得分
        tests.append(mk_pkt(0x02, 0x04, 0x04, 0x04, 0x00))  # triple record
        tests.append(mk_pkt(0x01, 0x03, 0x03, 0x03, 0x00))  # smaller triple -> 对手得分
        tests.append(mk_pkt(0x01, 0x00, 0x00, 0x00, 0x01))  # all_zero + state=0x01 -> 强制结束并判比分

        for i, pkt in enumerate(tests):
            QtCore.QTimer.singleShot(350 * i, lambda p=pkt: self.on_packet_received(p))

    def closeEvent(self, event):
        try:
            if self.reader:
                self.reader.stop_reading()
            if self.ser and getattr(self.ser, "is_open", False):
                self.ser.close()
        except:
            pass
        super().closeEvent(event)

# ========== 启动入口 ==========
def main():
    app = QtWidgets.QApplication(sys.argv)
    win = GameWindow()
    win.show()
    win.append_log("程序启动（双人扑克游戏助手）")
    return app.exec_()

if __name__ == "__main__":
    main()