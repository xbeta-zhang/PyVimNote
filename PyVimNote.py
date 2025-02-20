import sys
import os
import subprocess
from PyQt5.QtWidgets import QApplication, QMainWindow, QTreeView, QVBoxLayout, QWidget, QTextEdit, QSplitter, QMenu, QLineEdit
from PyQt5.QtCore import Qt, QModelIndex, QPoint
from PyQt5.QtGui import QFont, QTextCursor, QStandardItemModel, QStandardItem

class ZNoteQt(QMainWindow):
    def __init__(self):
        super().__init__()
        self.set_font_size = 12
        self.tree_font_size = self.set_font_size - 1
        self.h3_font_size = self.set_font_size + 2
        
        self.set_path = r"c:\users\zyx\Documents\我的坚果云\zyx2021\read"
        self.set_vim = r"C:\zapp\Vim\vim91\gvim.exe"
        
        # 获取屏幕尺寸（考虑任务栏）
        import win32api
        import win32con        
        self.screen = QApplication.primaryScreen().geometry()
        self.screen_width = self.screen.width()
        # 使用 Windows API 获取工作区高度（排除任务栏）
        self.work_height = win32api.GetSystemMetrics(win32con.SM_CYMAXIMIZED)
        
        # 计算窗口尺寸（1:2 比例）
        self.py_width = int(self.screen_width / 3)  # Python窗口占1/3
        self.vim_width = self.screen_width - self.py_width  # Vim窗口占2/3
        
        self.initUI()
        self.setup_gvim()

    def initUI(self):
        self.setWindowTitle('PyVimNote v1.0｜zyxβ2025-02')
        self.setGeometry(0, 0, self.py_width, self.work_height)
        
        # 创建主窗口的分割器
        splitter = QSplitter(Qt.Horizontal)
        splitter.setStyleSheet("""
            QSplitter::handle {
                background: none;
                height: 0px;
            }
        """)  # 隐藏分割线

        # 创建左侧面板容器
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(2, 2, 2, 2)  # 设置较小的边距
        left_layout.setSpacing(1)  # 减小控件间距

        # 创建搜索框并设置无边框样式
        self.search_box = QLineEdit()
        self.search_box.textChanged.connect(self.filter_files)
        left_layout.addWidget(self.search_box)

        # 创建标准项模型替代文件系统模型
        self.model = QStandardItemModel()
        
        # 创建目录树视图并设置无边框样式
        self.tree = QTreeView()
        self.tree.setStyleSheet("""
            QTreeView {
                border: none;
                background-color: transparent;
            }
            QTreeView::item {
                padding: 1px;
            }
        """)
        self.tree.setModel(self.model)
        self.tree.setFont(QFont('Microsoft YaHei Mono', self.tree_font_size))
        self.tree.clicked.connect(self.on_tree_select)
        self.tree.setHeaderHidden(True)
        
        left_layout.addWidget(self.tree)
        
        # 初始加载文件列表
        self.load_files()
        
        # 将左侧面板添加到分割器
        splitter.addWidget(left_panel)

        # 创建右侧面板容器
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(2, 2, 2, 2)
        right_layout.setSpacing(1)

        # 创建内容搜索框
        self.content_search = QLineEdit()
        self.content_search.returnPressed.connect(self.search_content)
        right_layout.addWidget(self.content_search)

        # 创建文本编辑器
        self.text = QTextEdit()
        self.text.setReadOnly(True)
        self.text.mousePressEvent = self.handle_single_click
        self.text.mouseDoubleClickEvent = self.handle_double_click
        right_layout.addWidget(self.text)

        # 将右侧面板添加到分割器
        splitter.addWidget(right_panel)

        # 设置分割器的比例 (1:2)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)

        self.setCentralWidget(splitter)

    def load_files(self):
        """加载所有文件到树形视图"""
        self.model.clear()
        self.file_paths = {}  # 存储文件路径映射
        
        def add_files_to_model(path, parent_item):
            for item in sorted(os.listdir(path)):
                item_path = os.path.join(path, item)
                if os.path.isfile(item_path) and item.endswith('.md'):
                    file_item = QStandardItem(item[:-3])  # 移除 .md 后缀
                    self.file_paths[item[:-3]] = item_path  # 保存完整路径
                    parent_item.appendRow(file_item)
                elif os.path.isdir(item_path):
                    dir_item = QStandardItem(item)
                    parent_item.appendRow(dir_item)
                    add_files_to_model(item_path, dir_item)

        add_files_to_model(self.set_path, self.model.invisibleRootItem())

    def filter_files(self, text):
        """过滤文件列表"""
        self.model.clear()
        root_item = self.model.invisibleRootItem()
        
        if not text:
            self.load_files()
            self.tree.expandAll()  # 确保空搜索时也展开
            return

        text = text.lower()
        
        def add_matching_files(path, parent_item):
            items_added = False
            for item in sorted(os.listdir(path)):
                item_path = os.path.join(path, item)
                if os.path.isfile(item_path) and item.endswith('.md'):
                    if text in item.lower():
                        file_item = QStandardItem(item[:-3])
                        self.file_paths[item[:-3]] = item_path
                        parent_item.appendRow(file_item)
                        items_added = True
                elif os.path.isdir(item_path):
                    dir_item = QStandardItem(item)
                    if add_matching_files(item_path, dir_item):
                        parent_item.appendRow(dir_item)
                        items_added = True
            return items_added

        add_matching_files(self.set_path, root_item)
        self.tree.expandAll()  # 过滤后直接展开所有节点

    def on_tree_select(self, index):
        """处理树形视图的选择事件"""
        item = self.model.itemFromIndex(index)
        if item and item.text() in self.file_paths:
            file_path = self.file_paths[item.text()]
            self.vim_open(file_path)
            search_term = os.path.splitext(os.path.basename(file_path))[0]
            self.show_backlinks(search_term)

    def find_title_line(self, cursor):
        """向上查找最近的标题行"""
        current_block = cursor.block()
        while current_block.isValid():
            text = current_block.text().strip()
            if text.startswith('# '):
                return text
            current_block = current_block.previous()
        return None

    def handle_single_click(self, event):
        if event.button() == Qt.LeftButton:
            cursor = self.text.cursorForPosition(event.pos())
            # 获取当前行并向上查找标题行
            title_line = self.find_title_line(cursor)
            
            if title_line:
                file_name = title_line[2:]
                file_path = os.path.join(self.set_path, file_name)
                if os.path.exists(file_path):
                    self.vim_open(file_path)
        
        # 确保调用父类的事件处理
        super(QTextEdit, self.text).mousePressEvent(event)

    def handle_double_click(self, event):
        if event.button() == Qt.LeftButton:
            cursor = self.text.cursorForPosition(event.pos())
            # 获取当前行并向上查找标题行
            title_line = self.find_title_line(cursor)
            
            if title_line:
                file_name = title_line[2:]
                file_path = os.path.join(self.set_path, file_name)
                if os.path.exists(file_path):
                    self.vim_open(file_path)
                    search_term = os.path.splitext(os.path.basename(file_name))[0]
                    print(f"双击更新双链，搜索词: {search_term}")
                    self.show_backlinks(search_term)
        
        # 确保调用父类的事件处理
        super(QTextEdit, self.text).mouseDoubleClickEvent(event)

    def search_and_display(self, search_terms):
        self.text.clear()
        results = {}
        
        # 将搜索词转换为小写
        search_terms_lower = [term.lower() for term in search_terms]
        
        # 设置文本格式
        self.text.document().setDefaultStyleSheet(f"""
            h3 {{
                color: #2060a0; 
                margin: 5px 0;
                font-size: {self.h3_font_size}pt;
            }}
            .highlight {{
                background-color: #FFEB3B;
            }}
            p {{
                margin: 2px 0;
                font-size: {self.set_font_size}pt;
            }}
        """)

        # 搜索文件
        for root, _, files in os.walk(self.set_path):
            for file in files:
                if file.endswith('.md'):
                    file_path = os.path.join(root, file)
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                            content_lower = content.lower()
                            
                            # 所有搜索词都必须出现
                            if all(term in content_lower for term in search_terms_lower):
                                # 获取包含搜索词的行
                                matching_lines = []
                                for line in content.split('\n'):
                                    line_lower = line.lower()
                                    if any(term in line_lower for term in search_terms_lower):
                                        matching_lines.append(line.strip())
                                if matching_lines:
                                    rel_path = os.path.relpath(file_path, self.set_path)
                                    results[rel_path] = matching_lines
                    except Exception as e:
                        print(f"Error reading file {file}: {e}")

        # 显示结果
        html_content = []
        if not results:
            html_content.append('0')
        else:
            for rel_path, lines in sorted(results.items()):
                html_content.append(f"<h3># {rel_path}</h3>")
                for line in lines:
                    highlighted_line = line
                    for term in search_terms:
                        highlighted_line = highlighted_line.replace(
                            term.lower(),
                            f'<span class="highlight">{term.lower()}</span>'
                        )
                        highlighted_line = highlighted_line.replace(
                            term.capitalize(),
                            f'<span class="highlight">{term.capitalize()}</span>'
                        )
                    html_content.append(f'<p>    {highlighted_line}</p>')
                html_content.append("<br>")

        self.text.setHtml('\n'.join(html_content))

    def show_backlinks(self, search_term):
        self.search_and_display([search_term])  # 移除 is_backlink 参数

    def vim_open(self, file_path):
        try:
            if not os.path.exists(file_path):
                print(f"文件不存在: {file_path}")
                return
                
            subprocess.Popen([
                self.set_vim,
                "--servername", "FILES",
                "--remote-silent",
                file_path
            ])
        except Exception as e:
            print(f"Error opening file with gvim: {e}")

    def setup_gvim(self):
        # 启动 gvim 并设置窗口
        set_home = r"c:\users\zyx\Documents\我的坚果云\zyx2021\0logseq\pages\2025-02q.md"
        self.vim_open(set_home)
        
        # 等待 GVim 窗口出现
        import time
        import win32gui
        import win32con
        
        time.sleep(0.5)  # 等待 GVim 启动
        gvim_hwnd = win32gui.FindWindow("Vim", None)
        
        if gvim_hwnd:
            # 设置 GVim 窗口位置和大小（靠右，占2/3宽度，考虑任务栏高度）
            win32gui.SetWindowPos(
                gvim_hwnd, 
                None,
                self.py_width,  # x 位置（从Python窗口右边开始）
                0,              # y 位置（顶部）
                self.vim_width, # 宽度（剩余2/3屏幕宽度）
                self.work_height,  # 高度（工作区高度，排除任务栏）
                win32con.SWP_NOZORDER | win32con.SWP_SHOWWINDOW
            )

    def search_content(self):
        """搜索笔记内容"""
        search_text = self.content_search.text().strip()
        if not search_text:
            return

        # 分割搜索词（最多取3个）
        search_terms = search_text.lower().split()[:3]
        self.search_and_display(search_terms)  # 移除 is_backlink 参数

def main():
    app = QApplication(sys.argv)
    
    ex = ZNoteQt()
    # 设置全局字体
    app.setFont(QFont('Microsoft YaHei Mono', ex.set_font_size))
    
    ex.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main() 
