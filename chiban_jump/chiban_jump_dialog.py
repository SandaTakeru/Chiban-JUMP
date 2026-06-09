# -*- coding: utf-8 -*-

import os

from qgis.PyQt import uic
from qgis.PyQt import QtWidgets
from qgis.PyQt.QtWidgets import QProgressDialog
from qgis.core import QgsVectorLayer
from qgis.PyQt.QtCore import Qt

FORM_CLASS, _ = uic.loadUiType(os.path.join(
	os.path.dirname(__file__), 'chiban_jump_dialog_base.ui'))


class ChibanJumpDialog(QtWidgets.QDialog, FORM_CLASS):
	def __init__(self, parent=None):
		super(ChibanJumpDialog, self).__init__(parent)
		self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)  # 常に最前面に表示
		self.setupUi(self)

		self.data_tree = {}

		self.chibankukaku.layerChanged.connect(self.initialize_data_tree)
		self.city_selector.currentIndexChanged.connect(self.populate_ooaza_selector)
		self.ooaza_selector.currentIndexChanged.connect(self.populate_chome_selector)
		self.chome_selector.currentIndexChanged.connect(self.populate_koaza_selector)
		self.koaza_selector.currentIndexChanged.connect(self.populate_yobi_selector)
		self.yobi_selector.currentIndexChanged.connect(self.populate_chiban_selector)

		self.initialize_data_tree()
		self.populate_city_selector()

	def initialize_data_tree(self):
		layer = self.chibankukaku.currentLayer()
		if not layer or not isinstance(layer, QgsVectorLayer):
			self.data_tree = {}
			self.populate_city_selector()
			return

		field_names = ['市区町村名', '大字名', '丁目名', '小字名', '予備名', '地番']
		layer_field_names = {field.name() for field in layer.fields()}
		field_indices = {name: layer.fields().indexFromName(name) for name in field_names if name in layer_field_names}

		total = layer.featureCount()
		progress = QProgressDialog('探索木を作成中...', 'キャンセル', 0, total, self)
		progress.setWindowModality(Qt.WindowModality.WindowModal)
		progress.setValue(0)

		self.data_tree = {}
		for i, feature in enumerate(layer.getFeatures()):
			if progress.wasCanceled():
				self.data_tree = {}
				break

			current_level = self.data_tree
			for field in field_names:
				if field in field_indices:
					raw = feature[field_indices[field]]
					value = 'NULL' if raw is None else str(raw)
				else:
					value = None
				if value not in current_level:
					current_level[value] = {}
				current_level = current_level[value]

			if i % 100 == 0:
				progress.setValue(i)

		progress.close()
		self.populate_city_selector()

	# --- ソートキー（静的メソッドで再生成コストを排除） ---

	@staticmethod
	def _sort_null_first(values, key=None):
		nulls = [v for v in values if v == 'NULL']
		non_nulls = [v for v in values if v != 'NULL']
		return nulls + sorted(non_nulls, key=key)

	@staticmethod
	def _sort_kanji(value):
		kanji_to_number = {'一': 1, '二': 2, '三': 3, '四': 4, '五': 5, '六': 6, '七': 7, '八': 8, '九': 9, '十': 10}

		def kanji_to_int(kanji):
			total = 0
			temp = 0
			for char in kanji:
				if char == '十':
					temp = temp * 10 if temp > 0 else 10
				elif char in kanji_to_number:
					temp += kanji_to_number[char]
				else:
					total += temp
					temp = 0
			return total + temp

		prefix = ''
		numeric_part = ''
		for char in value:
			if char in kanji_to_number or char == '十':
				numeric_part += char
			else:
				if numeric_part:
					break
				prefix += char
		return (prefix, kanji_to_int(numeric_part) if numeric_part else float('inf'))

	@staticmethod
	def _sort_chome(value):
		try:
			return int(value.replace('丁目', '').strip())
		except ValueError:
			return float('inf')

	@staticmethod
	def _sort_chiban(value):
		parts = value.split('-')
		return [int(part) if part.isdigit() else float('inf') for part in parts]

	# --- セレクタ更新（シグナルをブロックして多重カスケードを防ぐ） ---

	def populate_city_selector(self):
		self.city_selector.blockSignals(True)
		self.city_selector.clear()
		if self.data_tree:
			self.city_selector.addItems([''] + self._sort_null_first(self.data_tree.keys()))
			if len(self.data_tree) == 1:
				self.city_selector.setCurrentIndex(1)
		self.city_selector.blockSignals(False)
		self.populate_ooaza_selector()

	def populate_ooaza_selector(self):
		self.ooaza_selector.blockSignals(True)
		self.ooaza_selector.clear()
		selected_city = self.city_selector.currentText()
		if selected_city and selected_city in self.data_tree:
			values = self._sort_null_first(self.data_tree[selected_city].keys(), key=self._sort_kanji)
			self.ooaza_selector.addItems([''] + values)
			if len(values) == 1:
				self.ooaza_selector.setCurrentIndex(1)
		else:
			self.ooaza_selector.addItems([''])
		self.ooaza_selector.blockSignals(False)
		self.populate_chome_selector()

	def populate_chome_selector(self):
		self.chome_selector.blockSignals(True)
		self.chome_selector.clear()
		selected_city = self.city_selector.currentText()
		selected_ooaza = self.ooaza_selector.currentText()
		node = self.data_tree.get(selected_city, {}).get(selected_ooaza) if selected_city and selected_ooaza else None
		if node is not None:
			values = self._sort_null_first(node.keys(), key=self._sort_chome)
			self.chome_selector.addItems([''] + values)
			if len(values) == 1:
				self.chome_selector.setCurrentIndex(1)
		else:
			self.chome_selector.addItems([''])
		self.chome_selector.blockSignals(False)
		self.populate_koaza_selector()

	def populate_koaza_selector(self):
		self.koaza_selector.blockSignals(True)
		self.koaza_selector.clear()
		selected_city = self.city_selector.currentText()
		selected_ooaza = self.ooaza_selector.currentText()
		selected_chome = self.chome_selector.currentText()
		node = self.data_tree.get(selected_city, {}).get(selected_ooaza, {}).get(selected_chome) if selected_city and selected_ooaza and selected_chome else None
		if node is not None:
			values = self._sort_null_first(node.keys())
			self.koaza_selector.addItems([''] + values)
			if len(values) == 1:
				self.koaza_selector.setCurrentIndex(1)
		else:
			self.koaza_selector.addItems([''])
		self.koaza_selector.blockSignals(False)
		self.populate_yobi_selector()

	def populate_yobi_selector(self):
		self.yobi_selector.blockSignals(True)
		self.yobi_selector.clear()
		selected_city = self.city_selector.currentText()
		selected_ooaza = self.ooaza_selector.currentText()
		selected_chome = self.chome_selector.currentText()
		selected_koaza = self.koaza_selector.currentText()
		node = self.data_tree.get(selected_city, {}).get(selected_ooaza, {}).get(selected_chome, {}).get(selected_koaza) if selected_city and selected_ooaza and selected_chome and selected_koaza else None
		if node is not None:
			values = self._sort_null_first(node.keys())
			self.yobi_selector.addItems([''] + values)
			if len(values) == 1:
				self.yobi_selector.setCurrentIndex(1)
		else:
			self.yobi_selector.addItems([''])
		self.yobi_selector.blockSignals(False)
		self.populate_chiban_selector()

	def populate_chiban_selector(self):
		self.chiban_selector.clear()
		selected_city = self.city_selector.currentText()
		selected_ooaza = self.ooaza_selector.currentText()
		selected_chome = self.chome_selector.currentText()
		selected_koaza = self.koaza_selector.currentText()
		selected_yobi = self.yobi_selector.currentText()

		if not all([selected_city, selected_ooaza, selected_chome, selected_koaza, selected_yobi]):
			self.chiban_selector.addItems([''])
			return

		# ツリーを反復で辿る
		node = self.data_tree
		for key in [selected_city, selected_ooaza, selected_chome, selected_koaza, selected_yobi]:
			if key not in node:
				self.chiban_selector.addItems([''])
				return
			node = node[key]

		values = self._sort_null_first(node.keys(), key=self._sort_chiban)
		self.chiban_selector.addItems([''] + values)
		if len(values) == 1:
			self.chiban_selector.item(1).setSelected(True)
