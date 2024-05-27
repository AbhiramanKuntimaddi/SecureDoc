import sys
import os
import subprocess
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QPushButton, QFileDialog,
    QListWidget, QListWidgetItem, QLineEdit, QLabel, QProgressBar, QMessageBox, QListView
)
from PySide6.QtCore import Qt, QMimeData, QSize, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QPixmap, QIcon, QDrag
from PyPDF2 import PdfMerger
from pdf2image import convert_from_path


class PDFMergerLogic:
    def __init__(self):
        self.merger = PdfMerger()

    def merge_pdfs(self, pdf_files, output_file):
        try:
            for pdf in pdf_files:
                self.merger.append(pdf)
            self.merger.write(output_file)
            self.merger.close()
            return True, f'Merged PDF saved as {output_file}'
        except Exception as e:
            return False, str(e)


class AnimationHandler:
    def __init__(self):
        self.animations = []

    def animate_list_item(self, item):
        animation = QPropertyAnimation(item, b"size")
        animation.setDuration(500)
        animation.setStartValue(item.sizeHint() * 0.5)
        animation.setEndValue(item.sizeHint())
        animation.setEasingCurve(QEasingCurve.OutBounce)
        animation.start()
        self.animations.append(animation)

    def animate_progress_bar(self, progress_bar, value):
        animation = QPropertyAnimation(progress_bar, b"value")
        animation.setDuration(500)
        animation.setStartValue(progress_bar.value())
        animation.setEndValue(value)
        animation.setEasingCurve(QEasingCurve.InOutQuad)
        animation.start()
        self.animations.append(animation)


class ThumbnailListWidget(QListWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setViewMode(QListView.IconMode)
        self.setIconSize(QSize(100, 100))
        self.setSpacing(10)
        self.setAcceptDrops(True)
        self.setDragEnabled(True)
        self.setDropIndicatorShown(True)

    def dragEnterEvent(self, event):
        event.accept()

    def dragMoveEvent(self, event):
        event.accept()

    def dropEvent(self, event):
        if event.source() == self:
            event.setDropAction(Qt.MoveAction)
            super().dropEvent(event)
        else:
            event.ignore()

    def startDrag(self, supportedActions):
        item = self.currentItem()
        if item:
            drag = QDrag(self)
            mimeData = self.mimeData([item])
            drag.setMimeData(mimeData)
            pixmap = item.icon().pixmap(self.iconSize())
            drag.setPixmap(pixmap)
            drag.setHotSpot(pixmap.rect().center())
            drag.exec_(Qt.MoveAction)

    def add_pdf(self, pdf_path):
        try:
            images = convert_from_path(pdf_path, first_page=1, last_page=1, size=(100, 100))
            image = images[0].convert('RGB')
            qimage = image.toqpixmap().toImage()
            pixmap = QPixmap.fromImage(qimage)
            item = QListWidgetItem(QIcon(pixmap), pdf_path)
            item.setData(Qt.UserRole, pdf_path)
            self.addItem(item)
        except Exception as e:
            print(f"Error generating thumbnail for {pdf_path}: {e}")


class PDFMergerApp(QWidget):
    def __init__(self):
        super().__init__()
        self.pdf_merger_logic = PDFMergerLogic()
        self.animation_handler = AnimationHandler()
        self.initUI()

    def initUI(self):
        self.setWindowTitle('PDF Merger')
        self.setGeometry(100, 100, 600, 400)

        layout = QVBoxLayout()

        self.file_list = ThumbnailListWidget()
        self.select_files_btn = QPushButton('Select PDF Files')
        self.select_files_btn.clicked.connect(self.select_files)

        self.output_label = QLabel('Output File Name:')
        self.output_filename = QLineEdit()

        self.merge_btn = QPushButton('Merge PDFs')
        self.merge_btn.clicked.connect(self.merge_pdfs)

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)

        layout.addWidget(self.select_files_btn)
        layout.addWidget(self.file_list)
        layout.addWidget(self.output_label)
        layout.addWidget(self.output_filename)
        layout.addWidget(self.merge_btn)
        layout.addWidget(self.progress_bar)

        self.setLayout(layout)

    def select_files(self):
        files, _ = QFileDialog.getOpenFileNames(self, 'Select PDF Files', '', 'PDF Files (*.pdf)')
        if files:
            for file in files:
                self.file_list.add_pdf(file)

    def merge_pdfs(self):
        pdf_files = [self.file_list.item(i).data(Qt.UserRole) for i in range(self.file_list.count())]
        output_file = self.output_filename.text()

        if not pdf_files:
            QMessageBox.warning(self, 'Warning', 'No PDF files selected.')
            return

        if not output_file:
            QMessageBox.warning(self, 'Warning', 'Output file name not specified.')
            return

        if not output_file.endswith('.pdf'):
            output_file += '.pdf'

        success, message = self.pdf_merger_logic.merge_pdfs(pdf_files, output_file)

        if success:
            for i in range(len(pdf_files)):
                self.animation_handler.animate_progress_bar(self.progress_bar, int((i + 1) / len(pdf_files) * 100))
            QMessageBox.information(self, 'Success', message)
            self.open_folder(os.path.dirname(output_file))
        else:
            QMessageBox.critical(self, 'Error', f'Failed to merge PDFs: {message}')

    def open_folder(self, folder_path):
        if sys.platform == 'win32':
            os.startfile(folder_path)
        elif sys.platform == 'darwin':
            subprocess.Popen(['open', folder_path])
        else:
            subprocess.Popen(['xdg-open', folder_path])


if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = PDFMergerApp()
    ex.show()
    sys.exit(app.exec())
