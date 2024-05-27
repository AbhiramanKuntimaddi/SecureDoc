import sys
import os
import subprocess
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QFileDialog,
    QLineEdit, QLabel, QProgressBar, QMessageBox, QFrame, QGridLayout, QToolButton, QCheckBox
)
from PySide6.QtCore import Qt, QMimeData, QByteArray, QIODevice, QDataStream, QPoint, QRect, QSize
from PySide6.QtGui import QPixmap, QIcon, QDrag, QPainter, QColor, QFont, QPen, QCursor
from PyPDF2 import PdfMerger
from pdf2image import convert_from_path
import ntpath


class PDFMergerLogic:
    """Handles the logic for merging PDF files using PyPDF2."""

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


class PDFThumbnailWidget(QFrame):
    """Custom widget to display PDF thumbnail and a delete button."""

    def __init__(self, pdf_path, pixmap, parent=None):
        super().__init__(parent)
        self.pdf_path = pdf_path
        self.setFixedSize(120, 140)  # Adjusted size for square layout
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        # Create the thumbnail label
        self.thumbnail_label = QLabel()
        self.thumbnail_label.setPixmap(pixmap)
        self.thumbnail_label.setFixedSize(100, 100)
        self.thumbnail_label.setScaledContents(True)

        # Create a label for the PDF name
        name_label = QLabel(self.truncate_filename(ntpath.basename(pdf_path)))
        name_label.setAlignment(Qt.AlignCenter)
        name_label.setFont(QFont('Arial', 8, QFont.Bold))

        # Add the thumbnail and name label to the layout
        self.layout.addWidget(self.thumbnail_label)
        self.layout.addWidget(name_label)
        self.setFrameShape(QFrame.StyledPanel)
        self.setLineWidth(2)
        self.setAcceptDrops(True)

        # Create the delete button
        self.delete_button = QToolButton(self)
        self.delete_button.setText('X')
        self.delete_button.setStyleSheet("""
            QToolButton {
                color: red;
                border: 2px solid red;
                border-radius: 10px;
                background: white;
            }
        """)
        self.delete_button.setFixedSize(20, 20)
        self.delete_button.clicked.connect(self.delete_self)
        self.delete_button.move(self.width() - 20, 0)  # Move to top-right

    def truncate_filename(self, filename):
        """Truncate filename if it is too long."""
        return filename if len(filename) <= 15 else filename[:12] + '...'

    def delete_self(self):
        """Deletes the widget from the list when the delete button is clicked."""
        self.setParent(None)
        self.deleteLater()

    def get_pdf_path(self):
        """Returns the PDF file path associated with this thumbnail."""
        return self.pdf_path

    def mousePressEvent(self, event):
        """Handle the mouse press event to initiate drag."""
        if event.button() == Qt.LeftButton:
            drag = QDrag(self)
            mime_data = QMimeData()
            byte_array = QByteArray()
            stream = QDataStream(byte_array, QIODevice.WriteOnly)
            stream.writeInt32(self.pos().x())
            stream.writeInt32(self.pos().y())
            mime_data.setData("application/x-pdfthumbnailwidget", byte_array)
            drag.setMimeData(mime_data)
            drag.setPixmap(self.thumbnail_label.pixmap())
            drag.setHotSpot(event.position().toPoint())
            drag.exec(Qt.MoveAction)


class PlaceholderWidget(QFrame):
    """Placeholder widget with a '+' icon to add new PDFs."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(120, 140)
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)
        self.setStyleSheet("""
            QFrame {
                border: 2px dashed gray;
                border-radius: 10px;
            }
        """)

        self.add_button = QPushButton()
        self.add_button.setIcon(QIcon.fromTheme("list-add"))
        self.add_button.setIconSize(QSize(50, 50))
        self.add_button.setFlat(True)
        self.add_button.setStyleSheet("border: none;")

        add_label = QLabel("Add PDFs")
        add_label.setAlignment(Qt.AlignCenter)

        self.layout.addWidget(self.add_button, alignment=Qt.AlignCenter)
        self.layout.addWidget(add_label)

        self.setCursor(QCursor(Qt.PointingHandCursor))


class DraggableGridWidget(QFrame):
    """Custom QWidget that supports drag-and-drop for reordering items."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QGridLayout(self)
        self.layout.setSpacing(10)
        self.setLayout(self.layout)
        self.setAcceptDrops(True)
        self.highlight_rect = QRect()
        self.cell_width = 120
        self.cell_height = 140
        self.add_placeholder()

    def add_pdf(self, pdf_path):
        """Adds a PDF thumbnail to the grid."""
        try:
            images = convert_from_path(pdf_path, first_page=1, last_page=1, size=(100, 100))
            image = images[0].convert('RGB')
            qimage = image.toqpixmap().toImage()
            pixmap = QPixmap.fromImage(qimage)
            widget = PDFThumbnailWidget(pdf_path, pixmap)
            row, col = divmod(self.layout.count() - 1, 3)  # Exclude the placeholder
            self.layout.addWidget(widget, row, col)
            self.update_grid()
        except Exception as e:
            print(f"Error generating thumbnail for {pdf_path}: {e}")

    def add_placeholder(self):
        """Adds the placeholder widget to the grid."""
        self.placeholder = PlaceholderWidget()
        self.placeholder.add_button.clicked.connect(self.open_file_dialog)
        row, col = divmod(self.layout.count(), 3)
        self.layout.addWidget(self.placeholder, row, col)

    def open_file_dialog(self):
        """Opens the file dialog to select PDFs when the placeholder is clicked."""
        parent = self.parentWidget()
        if parent:
            parent.select_files()

    def dragEnterEvent(self, event):
        """Handles the drag enter event."""
        if event.mimeData().hasFormat("application/x-pdfthumbnailwidget"):
            event.acceptProposedAction()

    def dragMoveEvent(self, event):
        """Handles the drag move event."""
        if event.mimeData().hasFormat("application/x-pdfthumbnailwidget"):
            event.setDropAction(Qt.MoveAction)
            event.accept()
            # Highlight the potential drop position
            pos = event.position().toPoint()
            target_row, target_col = self.get_grid_position(pos)
            self.highlight_rect = self.layout.cellRect(target_row, target_col)
            self.update()

    def dropEvent(self, event):
        """Handles the drop event and reorders items."""
        if event.mimeData().hasFormat("application/x-pdfthumbnailwidget"):
            event.setDropAction(Qt.MoveAction)
            event.accept()

            # Read the data from the event
            byte_array = event.mimeData().data("application/x-pdfthumbnailwidget")
            stream = QDataStream(byte_array, QIODevice.ReadOnly)
            source_x = stream.readInt32()
            source_y = stream.readInt32()

            # Find the source widget
            source_widget = None
            for i in range(self.layout.count()):
                widget = self.layout.itemAt(i).widget()
                if widget and widget.pos() == QPoint(source_x, source_y):
                    source_widget = widget
                    break

            if source_widget and self.can_place():
                pos = event.position().toPoint()
                target_row, target_col = self.get_grid_position(pos)
                target_index = target_row * 3 + target_col
                self.swap_widgets(source_widget, target_index)
                self.update_grid()
                self.highlight_rect = QRect()
                self.update()

    def get_grid_position(self, pos):
        """Calculate the grid position from the mouse position."""
        row = pos.y() // self.cell_height
        col = pos.x() // self.cell_width
        return row, col

    def swap_widgets(self, source_widget, target_index):
        """Swaps the source widget with the widget at the target index."""
        items = [self.layout.itemAt(i).widget() for i in range(self.layout.count()) if self.layout.itemAt(i).widget() != self.placeholder]
        source_index = items.index(source_widget)
        items[source_index], items[target_index] = items[target_index], items[source_index]

        for index, widget in enumerate(items):
            row, col = divmod(index, 3)
            self.layout.addWidget(widget, row, col)

    def update_grid(self):
        """Rearranges the widgets in the grid layout."""
        items = [self.layout.itemAt(i).widget() for i in range(self.layout.count()) if self.layout.itemAt(i).widget() != self.placeholder]
        for i in reversed(range(self.layout.count())):
            widget = self.layout.itemAt(i).widget()
            self.layout.removeWidget(widget)

        for index, widget in enumerate(items):
            row, col = divmod(index, 3)
            self.layout.addWidget(widget, row, col)

        row, col = divmod(len(items), 3)
        self.layout.addWidget(self.placeholder, row, col)

    def clear_all_pdfs(self):
        """Clears all PDF thumbnails from the grid."""
        for i in reversed(range(self.layout.count())):
            widget = self.layout.itemAt(i).widget()
            if widget and widget != self.placeholder:
                self.layout.removeWidget(widget)
                widget.deleteLater()

    def get_pdf_paths(self):
        """Returns a list of PDF file paths in the current order."""
        pdf_paths = []
        for i in range(self.layout.count()):
            widget = self.layout.itemAt(i).widget()
            if widget and widget != self.placeholder:
                pdf_paths.append(widget.get_pdf_path())
        return pdf_paths

    def paintEvent(self, event):
        """Paint event to draw the highlight rectangle."""
        super().paintEvent(event)
        if not self.highlight_rect.isNull():
            painter = QPainter(self)
            pen = QPen(QColor(0, 255, 0), 3, Qt.DashLine) if self.can_place() else QPen(QColor(255, 0, 0), 3, Qt.DashLine)
            painter.setPen(pen)
            painter.drawRect(self.highlight_rect)

    def can_place(self):
        """Checks if the highlighted position is valid for placing the widget."""
        row, col = divmod(self.layout.count() - 1, 3)
        return self.highlight_rect.topLeft() != self.layout.cellRect(row, col).topLeft()


class PDFMergerApp(QWidget):
    """Main application window for the PDF Merger app."""

    def __init__(self):
        super().__init__()
        self.pdf_merger_logic = PDFMergerLogic()
        self.auto_name_enabled = False
        self.initUI()

    def initUI(self):
        """Initializes the user interface."""
        self.setWindowTitle('PDF Merger - PDF Reorder')
        self.setGeometry(100, 100, 600, 400)

        layout = QVBoxLayout()

        self.file_list = DraggableGridWidget()
        self.select_files_btn = QPushButton('Select PDF Files')
        self.select_files_btn.clicked.connect(self.select_files)
        self.select_files_btn.setStyleSheet("QPushButton { background-color: #4CAF50; color: white; border-radius: 5px; }")

        self.clear_all_btn = QPushButton('Clear All PDFs')
        self.clear_all_btn.clicked.connect(self.clear_all_pdfs)
        self.clear_all_btn.setStyleSheet("QPushButton { background-color: #f44336; color: white; border-radius: 5px; }")

        self.output_label = QLabel('Output File Name:')
        self.output_filename = QLineEdit()
        self.output_filename.setStyleSheet("QLineEdit { padding: 5px; border: 1px solid gray; border-radius: 5px; }")

        self.auto_name_checkbox = QCheckBox('Automatically name the output file')
        self.auto_name_checkbox.setStyleSheet("QCheckBox { margin-top: 10px; }")
        self.auto_name_checkbox.stateChanged.connect(self.toggle_auto_name)

        self.merge_btn = QPushButton('Merge PDFs')
        self.merge_btn.clicked.connect(self.merge_pdfs)
        self.merge_btn.setStyleSheet("QPushButton { background-color: #008CBA; color: white; border-radius: 5px; }")

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setStyleSheet("QProgressBar { border: 1px solid gray; border-radius: 5px; }")

        button_layout = QHBoxLayout()
        button_layout.addWidget(self.select_files_btn)
        button_layout.addWidget(self.clear_all_btn)

        output_layout = QHBoxLayout()
        output_layout.addWidget(self.output_label)
        output_layout.addWidget(self.output_filename)

        layout.addLayout(button_layout)
        layout.addWidget(self.file_list)
        layout.addLayout(output_layout)
        layout.addWidget(self.auto_name_checkbox)
        layout.addWidget(self.merge_btn)
        layout.addWidget(self.progress_bar)

        self.setLayout(layout)

    def toggle_auto_name(self, state):
        """Toggles the state of the output filename input based on the checkbox."""
        self.auto_name_enabled = state == Qt.Checked
        self.output_filename.setEnabled(not self.auto_name_enabled)
        if self.auto_name_enabled:
            self.output_filename.setText(self.generate_output_filename())
            self.output_filename.setStyleSheet("QLineEdit { background-color: #d3d3d3; color: #6c6c6c; cursor: not-allowed; }")
        else:
            self.output_filename.clear()
            self.output_filename.setStyleSheet("QLineEdit { padding: 5px; border: 1px solid gray; border-radius: 5px; }")

    def generate_output_filename(self):
        """Generates a unique output filename."""
        base_name = "Merged_Output"
        extension = ".pdf"
        counter = 1
        output_file = f"{base_name}{extension}"

        while os.path.exists(output_file):
            output_file = f"{base_name}_{counter:03d}{extension}"
            counter += 1

        return output_file

    def select_files(self):
        """Opens a file dialog to select PDF files and adds them to the grid."""
        files, _ = QFileDialog.getOpenFileNames(self, 'Select PDF Files', '', 'PDF Files (*.pdf)')
        if files:
            for file in files:
                self.file_list.add_pdf(file)

    def clear_all_pdfs(self):
        """Clears all PDF thumbnails from the grid."""
        self.file_list.clear_all_pdfs()

    def merge_pdfs(self):
        """Merges the selected PDF files and saves the output."""
        pdf_files = self.file_list.get_pdf_paths()
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
            QMessageBox.information(self, 'Success', message)
            self.open_folder(os.path.dirname(output_file))
        else:
            QMessageBox.critical(self, 'Error', f'Failed to merge PDFs: {message}')

    def open_folder(self, folder_path):
        """Opens the folder containing the merged PDF file."""
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
