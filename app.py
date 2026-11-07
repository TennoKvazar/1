"""OrthoSim prototype: geometric 3D dental-model editor, NOT a treatment planner."""
import os
os.environ.setdefault('QT_API', 'pyside6')

import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pyvista as pv
from pyvistaqt import QtInteractor
from PySide6.QtWidgets import (
    QApplication, QComboBox, QDoubleSpinBox, QFileDialog, QFormLayout,
    QGroupBox, QHBoxLayout, QLabel, QListWidget, QMainWindow, QMessageBox,
    QPushButton, QScrollArea, QVBoxLayout, QWidget,
)

from geometry import apply_at_current_center, apply_translation


@dataclass
class Model:
    name: str
    mesh: pv.PolyData
    matrix: np.ndarray = field(default_factory=lambda: np.eye(4))
    actor: object = None


class OrthoSim(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('OrthoSim 0.1 — геометрический 3D-прототип')
        self.resize(1350, 810)
        self.models: list[Model] = []
        self.stages: list[dict] = []

        outer = QWidget()
        self.setCentralWidget(outer)
        layout = QHBoxLayout(outer)
        layout.setContentsMargins(8, 8, 8, 8)

        panel = QWidget()
        panel.setMaximumWidth(350)
        sidebar = QVBoxLayout(panel)
        sidebar.setSpacing(9)
        scrolling = QScrollArea()
        scrolling.setWidgetResizable(True)
        scrolling.setWidget(panel)
        scrolling.setFixedWidth(370)
        layout.addWidget(scrolling)

        heading = QLabel('OrthoSim / 3D-редактор')
        heading.setStyleSheet('font-size: 19px; font-weight: 700;')
        sidebar.addWidget(heading)
        intro = QLabel('Прототип для обучения и разработки. Не моделирует силы, ткани и биологическое перемещение зубов.')
        intro.setWordWrap(True)
        intro.setStyleSheet('color: #c9a27a;')
        sidebar.addWidget(intro)

        self.add_button(sidebar, '1. Открыть демонстрационную модель', self.demo)
        self.add_button(sidebar, '2. Импортировать STL / PLY / OBJ', self.load_files)
        sidebar.addWidget(QLabel('Отдельный зуб = отдельный 3D-файл.'))
        self.items = QListWidget()
        self.items.setMinimumHeight(180)
        self.items.currentRowChanged.connect(self.update_selection)
        sidebar.addWidget(self.items)
        self.selection_label = QLabel('Не выбрана модель')
        self.selection_label.setWordWrap(True)
        sidebar.addWidget(self.selection_label)

        move_group = QGroupBox('Перемещение по осям, мм')
        move_layout = QVBoxLayout(move_group)
        move_controls = QFormLayout()
        self.move_step = QDoubleSpinBox()
        self.move_step.setRange(0.05, 10.0)
        self.move_step.setDecimals(2)
        self.move_step.setSingleStep(0.25)
        self.move_step.setValue(0.25)
        self.move_step.setSuffix(' мм')
        move_controls.addRow('Шаг:', self.move_step)
        move_layout.addLayout(move_controls)
        for axis in 'xyz':
            row = QHBoxLayout()
            row.addWidget(QLabel(axis.upper()))
            for sign, caption in ((-1, '−'), (1, '+')):
                button = QPushButton(caption)
                button.clicked.connect(lambda checked=False, a=axis, s=sign: self.move(a, s))
                row.addWidget(button)
            move_layout.addLayout(row)
        sidebar.addWidget(move_group)

        rot_group = QGroupBox('Поворот вокруг центра модели')
        rot_layout = QVBoxLayout(rot_group)
        rot_controls = QFormLayout()
        self.angle_step = QDoubleSpinBox()
        self.angle_step.setRange(0.5, 45.0)
        self.angle_step.setValue(2.0)
        self.angle_step.setSuffix('°')
        rot_controls.addRow('Шаг:', self.angle_step)
        rot_layout.addLayout(rot_controls)
        for axis in 'xyz':
            row = QHBoxLayout()
            row.addWidget(QLabel(axis.upper()))
            for sign, caption in ((-1, '−'), (1, '+')):
                button = QPushButton(caption)
                button.clicked.connect(lambda checked=False, a=axis, s=sign: self.rotate(a, s))
                row.addWidget(button)
            rot_layout.addLayout(row)
        sidebar.addWidget(rot_group)

        self.add_button(sidebar, 'Сбросить выбранную модель', self.reset_selected)
        self.add_button(sidebar, 'Сохранить этап в проекте', self.save_stage)
        self.stage_box = QComboBox()
        self.stage_box.addItem('Текущее состояние')
        sidebar.addWidget(self.stage_box)
        self.add_button(sidebar, 'Восстановить выбранный этап', self.restore_stage)
        self.add_button(sidebar, 'Экспортировать текущие STL + JSON', self.export)
        sidebar.addStretch(1)
        units = QLabel('Важно: для STL единицы измерения не хранятся. Перед работой убедись, что файл подготовлен в миллиметрах.')
        units.setWordWrap(True)
        units.setStyleSheet('color: #a3a3a3;')
        sidebar.addWidget(units)

        self.viewer = QtInteractor(outer)
        layout.addWidget(self.viewer, 1)
        self.viewer.set_background('#16212f')
        self.viewer.add_axes()
        self.viewer.show_grid()
        self.statusBar().showMessage('Для начала нажми «Открыть демонстрационную модель»')

    @staticmethod
    def add_button(layout, text, callback):
        button = QPushButton(text)
        button.setMinimumHeight(33)
        button.clicked.connect(callback)
        layout.addWidget(button)
        return button

    def current_model(self):
        i = self.items.currentRow()
        return self.models[i] if 0 <= i < len(self.models) else None

    def unique_name(self, name):
        existing = {item.name for item in self.models}
        if name not in existing:
            return name
        counter = 2
        while f'{name} ({counter})' in existing:
            counter += 1
        return f'{name} ({counter})'

    def add_model(self, name, mesh, color=None):
        if not isinstance(mesh, pv.PolyData):
            mesh = mesh.extract_surface()
        if mesh.n_points == 0:
            raise ValueError('В модели нет вершин')
        model = Model(self.unique_name(name), mesh.copy(deep=True))
        model.actor = self.viewer.add_mesh(model.mesh, name=f'obj-{len(self.models)}',
                                           color=color or '#e6d7bd', smooth_shading=True,
                                           show_edges=False)
        self.models.append(model)
        self.items.addItem(model.name)
        self.items.setCurrentRow(len(self.models) - 1)
        self.viewer.reset_camera()
        self.statusBar().showMessage(f'Добавлено: {model.name}')

    def demo(self):
        # Deliberately schematic objects; they are NOT anatomically accurate teeth.
        if self.models:
            decision = QMessageBox.question(self, 'Демонстрация',
                     'Очистить текущие модели и загрузить демонстрацию?')
            if decision != QMessageBox.StandardButton.Yes:
                return
        self.viewer.clear()
        self.viewer.add_axes()
        self.viewer.show_grid()
        self.models.clear()
        self.stages.clear()
        self.items.clear()
        self.stage_box.clear()
        self.stage_box.addItem('Текущее состояние')
        theta = np.linspace(-1.25, 1.25, 14)
        for index, angle in enumerate(theta, start=1):
            x = 25 * np.sin(angle)
            y = 25 * (1 - np.cos(angle))
            mesh = pv.ParametricEllipsoid(2.1, 2.65, 3.8)
            mesh.translate((x, y, 0), inplace=True)
            color = '#e5ddce' if index % 2 else '#cad7e4'
            self.add_model(f'Условный зуб {index:02d}', mesh, color)
        self.items.setCurrentRow(6)
        self.viewer.view_xy()
        self.viewer.reset_camera()
        self.statusBar().showMessage('Демонстрация: 14 условных зубов. Это НЕ диагностическая модель.')

    def load_files(self):
        paths, _ = QFileDialog.getOpenFileNames(self, 'Импорт 3D-моделей', '',
                                                 '3D-модели (*.stl *.ply *.obj)')
        if not paths:
            return
        failed = []
        for path in paths:
            try:
                mesh = pv.read(path)
                self.add_model(Path(path).stem, mesh)
            except Exception as exc:
                failed.append(f'{Path(path).name}: {exc}')
        if failed:
            QMessageBox.warning(self, 'Ошибки импорта', '\n'.join(failed[:12]))

    def update_selection(self):
        model = self.current_model()
        if model is None:
            self.selection_label.setText('Не выбрана модель')
            return
        self.selection_label.setText(f'Выбрана: {model.name}\nВершин: {model.mesh.n_points}')

    @staticmethod
    def set_actor_matrix(model):
        from vtkmodules.vtkCommonMath import vtkMatrix4x4
        vtkmat = vtkMatrix4x4()
        for i in range(4):
            for j in range(4):
                vtkmat.SetElement(i, j, float(model.matrix[i, j]))
        model.actor.SetUserMatrix(vtkmat)

    def apply_and_render(self, model):
        self.set_actor_matrix(model)
        self.viewer.render()
        self.statusBar().showMessage(f'Изменена геометрическая позиция: {model.name}')

    def move(self, axis, sign):
        model = self.current_model()
        if model is None:
            return
        model.matrix = apply_translation(model.matrix, axis, sign * self.move_step.value())
        self.apply_and_render(model)

    def rotate(self, axis, sign):
        model = self.current_model()
        if model is None:
            return
        model.matrix = apply_at_current_center(model.matrix, model.mesh.center,
                                               axis, sign * self.angle_step.value())
        self.apply_and_render(model)

    def reset_selected(self):
        model = self.current_model()
        if model is None:
            return
        model.matrix = np.eye(4)
        self.apply_and_render(model)

    def save_stage(self):
        if not self.models:
            return
        stage = {
            'title': f'Этап {len(self.stages) + 1}',
            'models': {model.name: model.matrix.tolist() for model in self.models},
        }
        self.stages.append(stage)
        self.stage_box.addItem(stage['title'])
        self.stage_box.setCurrentIndex(len(self.stages))
        self.statusBar().showMessage(f'Сохранён {stage["title"]}')

    def restore_stage(self):
        selected = self.stage_box.currentIndex()
        if selected == 0 or selected > len(self.stages):
            return
        matrices = self.stages[selected - 1]['models']
        for model in self.models:
            if model.name in matrices:
                model.matrix = np.asarray(matrices[model.name], dtype=float)
                self.set_actor_matrix(model)
        self.viewer.render()
        self.statusBar().showMessage('Этап восстановлен')

    def export(self):
        if not self.models:
            QMessageBox.information(self, 'Экспорт', 'Сначала открой модели или демонстрацию.')
            return
        folder = QFileDialog.getExistingDirectory(self, 'Папка для экспорта STL')
        if not folder:
            return
        target = Path(folder)
        manifest = {
            'software': 'OrthoSim 0.1',
            'purpose': 'geometric prototype; not a validated treatment simulation',
            'assumed_units': 'mm',
            'coordinate_system': 'original file axes; unregistered',
            'models': [],
            'saved_stages': self.stages,
        }
        try:
            for idx, model in enumerate(self.models, start=1):
                filename = f'model_{idx:02d}.stl'
                transformed = model.mesh.copy(deep=True)
                transformed.transform(model.matrix, inplace=True)
                transformed.triangulate().save(str(target / filename))
                manifest['models'].append({
                    'name': model.name,
                    'file': filename,
                    'transform': model.matrix.tolist(),
                })
            (target / 'orthosim_project.json').write_text(
                json.dumps(manifest, indent=2, ensure_ascii=False), encoding='utf-8')
        except Exception as exc:
            QMessageBox.critical(self, 'Ошибка экспорта', str(exc))
            return
        QMessageBox.information(self, 'Готово',
            f'Экспортировано моделей: {len(self.models)}\nПапка: {target}')

    def closeEvent(self, event):
        self.viewer.close()
        super().closeEvent(event)


def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    window = OrthoSim()
    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
