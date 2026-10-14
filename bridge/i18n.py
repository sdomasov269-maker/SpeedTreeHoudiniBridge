"""Localized plugin controls; native renderer diagnostics retain their original language."""
LANGUAGES = (("en", "English"), ("ru", "Русский"), ("ja", "日本語"), ("zh", "简体中文"), ("zh_TW", "繁體中文"))
KEYS = ("browse", "scale", "roughness", "normal", "flip", "scene", "camera", "dome", "sun", "view", "quarter", "front", "side", "import", "details", "ready", "busy", "done", "error", "materials", "polygons", "light", "unavailable")
ROWS = {
"en": ("Browse…", "Scale", "Roughness", "Normal strength", "Flip normal Y", "Scene", "Camera", "Soft light", "Sun", "Camera view", "Three-quarter", "Front", "Side", "Import tree", "Details", "Select a .stmat file", "Importing…", "Import complete", "Import failed", "Materials", "Polygons", "Light", "Renderer is not loaded"),
"ru": ("Выбрать…", "Масштаб", "Шероховатость", "Сила нормалей", "Инвертировать Y нормалей", "Сцена", "Камера", "Мягкий свет", "Солнце", "Ракурс камеры", "Три четверти", "Спереди", "Сбоку", "Импортировать дерево", "Подробности", "Выберите файл .stmat", "Импорт…", "Импорт завершён", "Ошибка импорта", "Материалы", "Полигоны", "Свет", "Рендер-плагин не загружен"),
"ja": ("参照…", "スケール", "ラフネス", "法線の強度", "法線の Y を反転", "シーン", "カメラ", "ソフトライト", "太陽", "カメラの角度", "斜め", "正面", "側面", "ツリーを読み込む", "詳細", ".stmat ファイルを選択", "読み込み中…", "読み込み完了", "読み込みエラー", "マテリアル", "ポリゴン", "ライト", "レンダラーがありません"),
"zh": ("浏览…", "缩放", "粗糙度", "法线强度", "翻转法线 Y", "场景", "相机", "柔光", "太阳", "相机视角", "斜视", "正面", "侧面", "导入树木", "详情", "选择 .stmat 文件", "正在导入…", "导入完成", "导入失败", "材质", "多边形", "灯光", "未加载渲染器"),
"zh_TW": ("瀏覽…", "縮放", "粗糙度", "法線強度", "翻轉法線 Y", "場景", "相機", "柔光", "太陽", "相機視角", "斜視", "正面", "側面", "匯入樹木", "詳細資訊", "選擇 .stmat 檔案", "正在匯入…", "匯入完成", "匯入失敗", "材質", "多邊形", "燈光", "未載入算圖引擎"),
}
LIVE_KEYS = ('live', 'auto_live', 'live_hint', 'live_update', 'live_busy', 'live_updated', 'live_ready', 'live_scene_changed', 'live_one_project')
LIVE_ROWS = {
    'en': ('Live transfer', 'Update after saving in SpeedTree', 'Select a saved .spm. The Modeler exports it in the background. Export units are centimeters; choose the initial scale.', 'Import / Update tree', 'Exporting from SpeedTree…', 'Tree updated', 'Saved project selected', 'Scene changed or Bridge closed during export; resend in the intended scene.', 'Select one .spm project for live transfer.'),
    'ru': ('Живая передача', 'Обновлять после сохранения в SpeedTree', 'Выберите сохранённый .spm. Modeler экспортирует его в фоне. Единицы экспорта — сантиметры; задайте начальный масштаб.', 'Импортировать / обновить дерево', 'Экспорт из SpeedTree…', 'Дерево обновлено', 'Проект выбран', 'Во время экспорта сцена изменилась или окно Bridge было закрыто. Повторите отправку в нужной сцене.', 'Для живой передачи выберите один проект .spm.'),
    'ja': ('ライブ転送', 'SpeedTree で保存後に更新', '保存済み .spm を選択。Modeler がバックグラウンドで書き出します。単位は cm です。初期スケールを設定してください。', 'ツリーを読み込み / 更新', 'SpeedTree から書き出し中…', 'ツリーを更新しました', '保存済みプロジェクトを選択', '書き出し中にシーンが変更されたか Bridge が閉じられました。目的のシーンに再送してください。', 'ライブ転送には .spm を 1 つ選択してください。'),
    'zh': ('实时传输', '在 SpeedTree 中保存后更新', '选择已保存的 .spm。Modeler 在后台导出，单位为厘米。请设置初始缩放。', '导入 / 更新树木', '正在从 SpeedTree 导出…', '树木已更新', '已选择项目', '导出期间场景改变或 Bridge 已关闭。请重新发送至目标场景。', '实时传输请选择一个 .spm 项目。'),
    'zh_TW': ('即時傳輸', '在 SpeedTree 儲存後更新', '選擇已儲存的 .spm。Modeler 在背景匯出，單位為公分。請設定初始縮放。', '匯入 / 更新樹木', '正在從 SpeedTree 匯出…', '樹木已更新', '已選擇專案', '匯出期間場景改變或 Bridge 已關閉。請重新傳送至目標場景。', '即時傳輸請選擇一個 .spm 專案。'),
}
ROWS = {code: row + LIVE_ROWS[code] for code, row in ROWS.items()}
KEYS += LIVE_KEYS
PAGE_KEYS = ('general_tab', 'materials_tab', 'render_tab', 'export_tab', 'renderer_label', 'karma_render', 'karma_engine', 'resolution_x', 'resolution_y', 'karma_samples', 'output_image', 'karma_hint', 'export_cache', 'export_preset', 'export_timeout', 'export_preset_missing')
PAGE_ROWS = {
    'en': ('General', 'Materials', 'Render', 'Export', 'Renderer', 'Solaris / Karma', 'Engine', 'Width', 'Height', 'Samples', 'Output image', 'These settings apply to Solaris / Karma. Render output is created automatically; rendering starts only when you request it.', 'Cache folder', 'Export preset', 'Timeout (sec)', 'Export preset file not found'),
    'ru': ('Общие', 'Материалы', 'Рендер', 'Экспорт', 'Рендерер', 'Solaris / Karma', 'Движок', 'Ширина', 'Высота', 'Сэмплы', 'Файл изображения', 'Эти настройки применяются к Solaris / Karma. Output создаётся автоматически; запуск рендера остаётся за вами.', 'Папка кэша', 'Пресет экспорта', 'Таймаут (сек)', 'Не найден файл пресета экспорта'),
    'ja': ('一般', 'マテリアル', 'レンダー', '書き出し', 'レンダラー', 'Solaris / Karma', 'エンジン', '幅', '高さ', 'サンプル', '出力画像', 'Solaris / Karma 用の設定です。出力ノードを自動作成します。レンダリングは手動で開始してください。', 'キャッシュ', '書き出しプリセット', 'タイムアウト（秒）', '書き出しプリセットが見つかりません'),
    'zh': ('常规', '材质', '渲染', '导出', '渲染器', 'Solaris / Karma', '引擎', '宽度', '高度', '采样', '输出图像', '这些设置用于 Solaris / Karma。自动创建输出节点，渲染由您手动启动。', '缓存目录', '导出预设', '超时（秒）', '未找到导出预设文件'),
    'zh_TW': ('一般', '材質', '算圖', '匯出', '算圖引擎', 'Solaris / Karma', '引擎', '寬度', '高度', '取樣', '輸出影像', '這些設定用於 Solaris / Karma。自動建立輸出節點，算圖由您手動啟動。', '快取資料夾', '匯出預設', '逾時（秒）', '找不到匯出預設檔案'),
}
ROWS = {code: row + PAGE_ROWS[code] for code, row in ROWS.items()}
KEYS += PAGE_KEYS
SOLARIS_KEYS = ('context_label', 'arnold_samples', 'redshift_samples', 'solaris_hint')
SOLARIS_ROWS = {
    'en': ('Scene workflow', 'Camera AA', 'Maximum samples', 'Solaris creates renderer-specific materials, render settings and an output node automatically.'),
    'ru': ('Режим сцены', 'Camera AA', 'Максимум сэмплов', 'Solaris автоматически создаёт материалы, настройки рендера и Output для выбранного движка.'),
    'ja': ('シーンモード', 'Camera AA', '最大サンプル数', 'Solaris は選択したレンダラー用のマテリアル、設定、出力ノードを自動作成します。'),
    'zh': ('场景模式', 'Camera AA', '最大采样数', 'Solaris 自动创建所选渲染器的材质、渲染设置和输出节点。'),
    'zh_TW': ('場景模式', 'Camera AA', '最大取樣數', 'Solaris 自動建立所選算圖引擎的材質、算圖設定和輸出節點。'),
}
ROWS = {code: row + SOLARIS_ROWS[code] for code, row in ROWS.items()}
KEYS += SOLARIS_KEYS
TRANSLATIONS = {code: dict(zip(KEYS, row)) for code, row in ROWS.items()}
def translate(code, key):
    return TRANSLATIONS.get(code, TRANSLATIONS["en"])[key]
