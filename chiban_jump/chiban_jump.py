from qgis.PyQt.QtCore import QSettings, QTranslator, QCoreApplication
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction
from qgis.core import (
	QgsExpression,
	QgsFeatureRequest,
	QgsGeometry,
	QgsMapLayerProxyModel,
	Qgis
)

from .resources import *
from .chiban_jump_dialog import ChibanJumpDialog
import os.path


class ChibanJump:
	def __init__(self, iface):
		self.iface = iface
		self.plugin_dir = os.path.dirname(__file__)
		locale = QSettings().value('locale/userLocale')[0:2]
		locale_path = os.path.join(
			self.plugin_dir,
			'i18n',
			'ChibanJump_{}.qm'.format(locale))

		if os.path.exists(locale_path):
			self.translator = QTranslator()
			self.translator.load(locale_path)
			QCoreApplication.installTranslator(self.translator)

		self.actions = []
		self.menu = self.tr(u'&地番JUMP')
		self.first_start = None

	def tr(self, message):
		return QCoreApplication.translate('ChibanJump', message)

	def add_action(
		self,
		icon_path,
		text,
		callback,
		enabled_flag=True,
		add_to_menu=True,
		add_to_toolbar=True,
		status_tip=None,
		whats_this=None,
		parent=None):
		icon = QIcon(icon_path)
		action = QAction(icon, text, parent)
		action.triggered.connect(callback)
		action.setEnabled(enabled_flag)

		if status_tip is not None:
			action.setStatusTip(status_tip)

		if whats_this is not None:
			action.setWhatsThis(whats_this)

		if add_to_toolbar:
			self.iface.addToolBarIcon(action)

		if add_to_menu:
			self.iface.addPluginToVectorMenu(
				self.menu,
				action)

		self.actions.append(action)

		return action

	def initGui(self):
		icon_path = os.path.join(self.plugin_dir, 'icon.png')  # icon.png を指定
		self.add_action(
			icon_path,
			text=self.tr(u'地番JUMP'),
			callback=self.run,
			parent=self.iface.mainWindow())

		self.first_start = True

	def unload(self):
		for action in self.actions:
			self.iface.removePluginVectorMenu(
				self.tr(u'&地番JUMP'),
				action)
			self.iface.removeToolBarIcon(action)

	def build_conditions(self, fields):
		conditions = []
		for field, value in fields.items():
			if value is not None and value.strip():
				if value == 'NULL':
					conditions.append(f'"{field}" IS NULL')
				else:
					escaped = value.replace("'", "''")
					conditions.append(f'"{field}" = \'{escaped}\'')
		return conditions

	def run(self):
		if self.first_start:
			self.first_start = False
			self.dlg = ChibanJumpDialog()

			# chibankukaku にポリゴンレイヤのフィルタを設定
			self.dlg.chibankukaku.setFilters(QgsMapLayerProxyModel.PolygonLayer)

		# アクティブレイヤをプリセット
		active_layer = self.iface.activeLayer()
		if active_layer:
			self.dlg.chibankukaku.setLayer(active_layer)

		self.dlg.show()
		result = self.dlg.exec()
		if result:
			# 選択したレイヤを取得
			selected_layer = self.dlg.chibankukaku.currentLayer()

			# 各フィールドの値を取得
			city = self.dlg.city_selector.currentText()
			ooaza = self.dlg.ooaza_selector.currentText()
			chome = self.dlg.chome_selector.currentText()
			koaza = self.dlg.koaza_selector.currentText()
			yobi = self.dlg.yobi_selector.currentText()

			# 地番は複数選択（空白・未選択はフィルタなし）
			selected_chiban = [item.text() for item in self.dlg.chiban_selector.selectedItems() if item.text()]

			if selected_layer:
				# 上位フィールドの条件式を構築
				fields = {
					"市区町村名": city,
					"大字名": ooaza,
					"丁目名": chome,
					"小字名": koaza,
					"予備名": yobi,
				}
				conditions = self.build_conditions(fields)

				# 地番の条件を追加（複数選択対応）
				if selected_chiban:
					if len(selected_chiban) == 1:
						v = selected_chiban[0]
						conditions.append('"地番" IS NULL' if v == 'NULL' else f'"地番" = \'{v}\'')
					else:
						null_vals = [v for v in selected_chiban if v == 'NULL']
						str_vals = [v for v in selected_chiban if v != 'NULL']
						chiban_parts = []
						if str_vals:
							in_list = ', '.join(f"'{v.replace(chr(39), chr(39)*2)}'" for v in str_vals)
							chiban_parts.append(f'"地番" IN ({in_list})')
						if null_vals:
							chiban_parts.append('"地番" IS NULL')
						conditions.append(f'({" OR ".join(chiban_parts)})')

				if conditions:
					expression = QgsExpression(" AND ".join(conditions))
					request = QgsFeatureRequest(expression)
					selected_features = [f for f in selected_layer.getFeatures(request)]

					if selected_features:
						final_ids = {f.id() for f in selected_features}

						# 隣接地も選択するオプション
						if self.dlg.adjacent_checkbox.isChecked():
							valid_geoms = [f.geometry() for f in selected_features if f.geometry() and not f.geometry().isEmpty()]
							if valid_geoms:
								union_geom = QgsGeometry.unaryUnion(valid_geoms)
								bbox_request = QgsFeatureRequest().setFilterRect(union_geom.boundingBox()).setSubsetOfAttributes([])
								for candidate in selected_layer.getFeatures(bbox_request):
									if candidate.id() not in final_ids and union_geom.touches(candidate.geometry()):
										final_ids.add(candidate.id())

						selected_layer.selectByIds(list(final_ids))
						self.iface.mapCanvas().zoomToSelected(selected_layer)
					else:
						self.iface.messageBar().pushMessage(
							"情報", "該当する地物が見つかりませんでした。条件を確認してください。", level=Qgis.Info)
				else:
					self.iface.messageBar().pushMessage(
						"エラー", "検索条件が入力されていません。すべてのフィールドが空白です。", level=Qgis.Critical)
			else:
				self.iface.messageBar().pushMessage(
					"エラー", "レイヤが選択されていません。ポリゴンレイヤを選択してください。", level=Qgis.Critical)