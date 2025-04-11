import sys
import os
import json
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, 
    QHBoxLayout, QPushButton, QLabel, QInputDialog, 
    QMessageBox, QStackedWidget, QScrollArea
)
from PyQt5.QtWebEngineWidgets import QWebEngineView, QWebEngineProfile, QWebEnginePage
from PyQt5.QtWebEngineCore import QWebEngineCookieStore
from PyQt5.QtWebChannel import QWebChannel
from PyQt5.QtCore import Qt, QUrl, QObject, pyqtSlot
from PyQt5.QtGui import QFont

class SessionButton(QWidget):
    def __init__(self, session_name, parent=None):
        super().__init__(parent)
        self.session_name = session_name
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # 버튼과 타이틀이 있는 컨테이너
        self.button_container = QWidget()
        button_layout = QHBoxLayout(self.button_container)
        button_layout.setContentsMargins(0, 0, 0, 0)
        button_layout.setSpacing(5)
        
        # 메인 버튼
        self.main_button = QPushButton(session_name)
        self.main_button.setMinimumHeight(40)
        self.main_button.setFont(QApplication.font())
        self.main_button.setCheckable(True)
        
        # 페이지 타이틀 레이블
        self.title_label = QLabel("")
        self.title_label.setFont(QApplication.font())
        self.title_label.setStyleSheet("color: #666; font-size: 11px;")
        
        # X 버튼
        self.close_button = QPushButton("×")
        self.close_button.setFixedSize(40, 40)
        close_font = QApplication.font()
        close_font.setPointSize(16)
        self.close_button.setFont(close_font)
        
        # 스타일 설정
        self.setStyleSheet("""
            QPushButton#main {
                text-align: left;
                padding: 5px 10px;
                border: 1px solid #ccc;
                border-top-left-radius: 5px;
                border-bottom-left-radius: 5px;
                background-color: #f8f9fa;
                border-right: none;
            }
            QPushButton#main:hover {
                background-color: #e9ecef;
            }
            QPushButton#main:checked {
                background-color: #ff8a3d;
                color: white;
                border: none;
            }
            QPushButton#close {
                border: 1px solid #ccc;
                border-top-right-radius: 5px;
                border-bottom-right-radius: 5px;
                background-color: #f8f9fa;
                color: #666;
            }
            QPushButton#close:hover {
                background-color: #dc3545;
                color: white;
                border-color: #dc3545;
            }
            QLabel#badge {
                background-color: #dc3545;
                color: white;
                border-radius: 12px;
                font-size: 11px;
                padding: 2px;
            }
            QLabel#badge[urgent="true"] {
                background-color: #ff8a3d;
            }
        """)
        
        self.main_button.setObjectName("main")
        self.close_button.setObjectName("close")
        
        button_layout.addWidget(self.main_button)
        button_layout.addWidget(self.title_label)
        
        layout.addWidget(self.button_container)
        layout.addWidget(self.close_button)
    
    def update_page_title(self, title):
        """페이지 타이틀 업데이트"""
        if title:
            # 타이틀이 (로 시작하는 경우 괄호 안의 숫자만 표시
            if title.startswith('('):
                import re
                match = re.match(r'\((\d+)\)', title)
                if match:
                    self.title_label.setText(f"- {match.group(1)}개")
                    return

            # 기존 로직: 타이틀이 너무 길면 잘라내기
            short_title = title[:20] + "..." if len(title) > 20 else title
            self.title_label.setText(f"- {short_title}")
        else:
            self.title_label.setText("")
            
    def setChecked(self, checked):
        self.main_button.setChecked(checked)
        
    def isChecked(self):
        return self.main_button.isChecked()

class BrowserSession(QWidget):
    def __init__(self, session_name, profile_path, parent=None):
        super().__init__(parent)
        self.session_name = session_name
        self.notification_count = 0
        
        # 세션별 프로필 설정
        self.profile = QWebEngineProfile(session_name)
        self.profile.setPersistentStoragePath(profile_path)
        self.profile.setPersistentCookiesPolicy(QWebEngineProfile.ForcePersistentCookies)
        
        # 브라우저 생성
        self.web_view = QWebEngineView()
        self.web_page = QWebEnginePage(self.profile, self.web_view)
        self.web_view.setPage(self.web_page)
        
        # JavaScript 브릿지 설정
        self.web_page.titleChanged.connect(self.on_title_changed)
        self.web_page.loadFinished.connect(self.on_page_load)
        
        # 레이아웃 설정
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.web_view)
        
        # 당근마켓 채팅 페이지 로드
        self.web_view.setUrl(QUrl("https://chat.daangn.com/login"))

    def handle_permission_request(self, origin, feature):
        """권한 요청 처리"""
        from PyQt5.QtWebEngineWidgets import QWebEnginePage
        if feature == QWebEnginePage.Notifications:
            self.web_page.setFeaturePermission(
                origin, 
                feature,
                QWebEnginePage.PermissionGrantedByUser
            )
    
    def on_page_load(self, ok):
        """페이지 로드 완료 시 처리"""
        if ok:
            # 타이틀 변경 감지를 위한 JavaScript 코드
            script = """
            // 타이틀 변경 감지 함수
            function watchTitle() {
                // 이전 타이틀 저장
                let previousTitle = document.title;
                
                // 타이틀 변경 감시
                setInterval(() => {
                    if (document.title !== previousTitle) {
                        // 알림 개수 파싱
                        const match = document.title.match(/^\((\d+)\)/);
                        const notificationCount = match ? parseInt(match[1]) : 0;
                        
                        // Qt 브릿지를 통해 알림 개수 전달
                        window.qt.notifyNewMessage(notificationCount);
                        
                        previousTitle = document.title;
                    }
                }, 1000);
            }
            
            // 실행
            watchTitle();
            """
            
            # 브라우저에 Qt 브릿지 추가
            self.channel = QWebChannel(self.web_page)
            self.web_page.setWebChannel(self.channel)
            
            # JavaScript에서 호출할 수 있는 객체 정의
            class Bridge(QObject):
                def __init__(self, callback):
                    super().__init__()
                    self.callback = callback
                    
                @pyqtSlot(int)
                def notifyNewMessage(self, count):
                    self.callback(count)
            
            self.bridge = Bridge(self.handle_new_message)
            self.channel.registerObject('qt', self.bridge)
            
            # JavaScript 코드 실행
            self.web_page.runJavaScript(script)
    
    def set_title_callback(self, callback):
        """타이틀 변경 콜백 설정"""
        self.title_callback = callback
        
    def on_title_changed(self, title):
        """페이지 타이틀 변경 처리"""
        if hasattr(self, 'title_callback'):
            self.title_callback(self.session_name, title)

    def set_notification_callback(self, callback):
        """알림 콜백 설정"""
        self.notification_callback = callback
        
    def handle_new_message(self, count):
        """새 메시지 개수 처리"""
        if hasattr(self, 'notification_callback') and count != self.notification_count:
            self.notification_count = count
            self.notification_callback(self.session_name, count)

class SessionManagerGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.sessions = {}
        self.session_buttons = {}
        self.base_profile_path = os.path.join(os.path.expanduser("~"), "daangn_profiles")
        self.sessions_file = os.path.join(self.base_profile_path, "sessions.json")
        
        if not os.path.exists(self.base_profile_path):
            os.makedirs(self.base_profile_path)
            
        self.init_ui()
        self.load_sessions()
        
    def handle_notification(self, session_name, count):
        """세션별 알림 처리"""
        if session_name in self.session_buttons:
            self.session_buttons[session_name].update_notification_count(count)
            # 시스템 트레이 알림 표시 (옵션)
            if session_name != self.get_active_session():
                QApplication.instance().alert(self)
                
    def handle_title_change(self, session_name, title):
        """세션별 타이틀 처리"""
        if session_name in self.session_buttons:
            self.session_buttons[session_name].update_page_title(title)

    def get_active_session(self):
        """현재 활성화된 세션 이름 반환"""
        for name, button in self.session_buttons.items():
            if button.isChecked():
                return name
        return None

    def init_ui(self):
        """GUI 초기화"""
        self.setWindowTitle('당근 채팅 멀티 세션 매니저')
        self.setGeometry(100, 100, 1200, 800)

        # 메인 위젯 설정
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout(main_widget)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # 좌측 컨트롤 패널
        control_panel = QWidget()
        control_panel.setMaximumWidth(250)
        control_panel.setMinimumWidth(200)
        control_layout = QVBoxLayout(control_panel)
        control_layout.setContentsMargins(10, 10, 10, 10)
        
        # 새 세션 추가 버튼
        self.add_btn = QPushButton('+ 새 세션 추가')
        self.add_btn.setStyleSheet("""
            QPushButton {
                background-color: #ff8a3d;
                color: white;
                border: none;
                padding: 8px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #ff9f40;
            }
        """)
        self.add_btn.clicked.connect(self.add_session)
        control_layout.addWidget(self.add_btn)
        
        # 세션 버튼을 담을 스크롤 영역
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; }")
        
        self.session_button_container = QWidget()
        self.session_button_layout = QVBoxLayout(self.session_button_container)
        self.session_button_layout.addStretch()
        scroll.setWidget(self.session_button_container)
        control_layout.addWidget(scroll)

        # 우측 브라우저 스택
        self.browser_stack = QStackedWidget()
        
        # 레이아웃 조합
        main_layout.addWidget(control_panel)
        main_layout.addWidget(self.browser_stack)
        
        # 상태 표시줄
        self.statusBar().showMessage('준비')

    def load_sessions(self):
        """저장된 세션 정보 로드"""
        if os.path.exists(self.sessions_file):
            with open(self.sessions_file, 'r', encoding='utf-8') as f:
                saved_sessions = json.load(f)
                for session_name in saved_sessions:
                    self.create_session(session_name)

    def save_sessions(self):
        """현재 세션 정보 저장"""
        sessions_data = {name: {"profile_path": os.path.join(self.base_profile_path, name)} 
                        for name in self.sessions.keys()}
        with open(self.sessions_file, 'w', encoding='utf-8') as f:
            json.dump(sessions_data, f, ensure_ascii=False, indent=2)

    def create_session(self, session_name):
        """새 브라우저 세션 생성"""
        profile_path = os.path.join(self.base_profile_path, session_name)
        if not os.path.exists(profile_path):
            os.makedirs(profile_path)

        # 브라우저 세션 생성
        browser_session = BrowserSession(session_name, profile_path)
        browser_session.set_title_callback(self.handle_title_change)
        browser_session.set_notification_callback(self.handle_notification)
        self.sessions[session_name] = browser_session
        self.browser_stack.addWidget(browser_session)
        
        # 세션 버튼 생성
        button = SessionButton(session_name)
        button.main_button.clicked.connect(lambda: self.switch_session(session_name))
        button.close_button.clicked.connect(lambda: self.remove_session(session_name))
        button.main_button.setContextMenuPolicy(Qt.CustomContextMenu)
        button.main_button.customContextMenuRequested.connect(
            lambda pos: self.show_session_menu(pos, session_name))
        self.session_buttons[session_name] = button
        
        # 버튼을 stretch 앞에 추가
        self.session_button_layout.insertWidget(
            self.session_button_layout.count() - 1, button)
            
        # 첫 번째 세션이면 활성화
        if len(self.sessions) == 1:
            self.switch_session(session_name)
            
        self.save_sessions()

    def switch_session(self, session_name):
        """세션 전환"""
        if session_name not in self.sessions or session_name not in self.session_buttons:
            return
            
        # 모든 버튼 체크 해제
        for button in self.session_buttons.values():
            button.setChecked(False)
        
        # 선택된 세션 버튼 체크
        self.session_buttons[session_name].setChecked(True)
        
        # 브라우저 전환
        self.browser_stack.setCurrentWidget(self.sessions[session_name])
        self.statusBar().showMessage(f'세션: {session_name}')

    def show_session_menu(self, pos, session_name):
        """세션 컨텍스트 메뉴"""
        from PyQt5.QtWidgets import QMenu
        menu = QMenu()
        rename_action = menu.addAction("이름 변경")
        delete_action = menu.addAction("세션 삭제")
        action = menu.exec_(self.session_buttons[session_name].main_button.mapToGlobal(pos))
        
        if action == delete_action:
            self.remove_session(session_name)
        elif action == rename_action:
            self.rename_session(session_name)

    def add_session(self):
        """새 세션 추가"""
        session_name, ok = QInputDialog.getText(self, '세션 추가', 
            '새 세션의 이름을 입력하세요:')
        
        if ok and session_name:
            if session_name in self.sessions:
                QMessageBox.warning(self, '경고', '이미 존재하는 세션 이름입니다.')
                return
                
            try:
                self.create_session(session_name)
                self.statusBar().showMessage(f'세션 {session_name} 생성됨')
            except Exception as e:
                QMessageBox.critical(self, '오류', f'세션 생성 실패: {str(e)}')

    def rename_session(self, old_name):
        """세션 이름 변경"""
        new_name, ok = QInputDialog.getText(self, '세션 이름 변경', 
            '새 이름을 입력하세요:', text=old_name)
        
        if ok and new_name and new_name != old_name:
            if new_name in self.sessions:
                QMessageBox.warning(self, '경고', '이미 존재하는 세션 이름입니다.')
                return
                
            try:
                # 브라우저 세션 이름 변경
                browser_session = self.sessions.pop(old_name)
                browser_session.session_name = new_name
                self.sessions[new_name] = browser_session
                
                # 버튼 업데이트
                button = self.session_buttons.pop(old_name)
                button.session_name = new_name
                button.main_button.setText(new_name)
                self.session_buttons[new_name] = button
                
                # 이벤트 핸들러 재연결
                button.main_button.clicked.disconnect()
                button.close_button.clicked.disconnect()
                button.main_button.clicked.connect(lambda: self.switch_session(new_name))
                button.close_button.clicked.connect(lambda: self.remove_session(new_name))
                
                # 컨텍스트 메뉴 재연결
                button.main_button.customContextMenuRequested.disconnect()
                button.main_button.customContextMenuRequested.connect(
                    lambda pos: self.show_session_menu(pos, new_name))
                
                # 프로필 디렉토리 이름 변경
                old_path = os.path.join(self.base_profile_path, old_name)
                new_path = os.path.join(self.base_profile_path, new_name)
                if os.path.exists(old_path):
                    os.rename(old_path, new_path)
                
                self.save_sessions()
                self.statusBar().showMessage(f'세션 이름이 {new_name}(으)로 변경됨')
                
                # 현재 활성 세션이었다면 switch_session 호출
                if button.isChecked():
                    self.switch_session(new_name)
                    
            except Exception as e:
                QMessageBox.critical(self, '오류', f'이름 변경 실패: {str(e)}')

    def remove_session(self, session_name):
        """세션 삭제"""
        reply = QMessageBox.question(self, '세션 삭제', 
            f'세션 {session_name}을(를) 삭제하시겠습니까?',
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)

        if reply == QMessageBox.Yes:
            # 브라우저 세션 제거
            self.browser_stack.removeWidget(self.sessions[session_name])
            self.sessions[session_name].deleteLater()
            del self.sessions[session_name]
            
            # 버튼 제거
            self.session_buttons[session_name].deleteLater()
            del self.session_buttons[session_name]
            
            # 다른 세션으로 전환
            if self.sessions:
                next_session = list(self.sessions.keys())[0]
                self.switch_session(next_session)
                
            self.save_sessions()
            self.statusBar().showMessage(f'세션 {session_name} 삭제됨')

    def closeEvent(self, event):
        """프로그램 종료 처리"""
        reply = QMessageBox.question(self, '종료', 
            '프로그램을 종료하시겠습니까?',
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)

        if reply == QMessageBox.Yes:
            self.save_sessions()
            event.accept()
        else:
            event.ignore()

def check_expiration():
    """프로그램 만료일 체크"""
    from datetime import datetime
    expiration_date = datetime(2024, 2, 5)
    current_date = datetime.now()
    
    if current_date > expiration_date:
        app = QApplication(sys.argv)
        QMessageBox.critical(None, '프로그램 만료', 
            '이 프로그램의 사용 기한이 만료되었습니다.\n사용 기한: ~2024년 2월 5일')
        sys.exit(1)

def main():
    # 만료일 체크
    check_expiration()
    
    # High DPI 지원
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)
    
    app = QApplication(sys.argv)
    
    # 기본 폰트 설정
    default_font = app.font()
    default_font.setPointSize(10)
    app.setFont(default_font)
    
    ex = SessionManagerGUI()
    ex.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()