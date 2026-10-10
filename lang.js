// The plugin's words in Russian (as Hyimg's own plugins do, owner 2026-10-06: «make 2 versions, Russian and English, switchable in
// settings»). The code writes the English text, this file gives the Russian; Hyimg's board picks by its language setting (HY.lang). Every
// key goes to the board under the prefix «dev::», so a word of this plugin never changes the same English word elsewhere on the board.
// en: only plural forms. A Hyimg without HY.t shows the English. Short labels have no full stop at the end.
const P = "dev::";
const RU = {
  // the card
  "HTML page: double-click for Dev Studio": "HTML-страница: двойной клик открывает Dev Studio",
  "HTML page": "HTML-страница",
  "Double-click or Dev Studio in the dock to edit the page": "Двойной клик или Dev Studio в доке, чтобы править страницу",
  // the dock's mode switch: the short label, the studio's name (owner 2026-10-08: Dev Studio)
  "Dev": "Дев",
  "Dev Studio": "Dev Studio",
  "Dev Studio for the selected HTML card: the page's tree, the live page, the inspector": "Dev Studio для выбранной HTML-карточки: дерево страницы, живая страница, инспектор",
  "Select an HTML card or enter one: Dev Studio opens for it": "Выбери HTML-карточку или войди в нее: для нее откроется Dev Studio",
  "Open an HTML card to use Dev Studio": "Открой HTML-карточку, чтобы перейти в Dev Studio",
  // Dev Studio
  "Find element": "Найти элемент",
  "Properties": "Свойства",
  "Elements": "Элементы",
  "Nothing found": "Ничего не найдено",
  "Loading the page…": "Загружаю страницу…",
  "The page did not answer: it may block scripts or its file is gone": "Страница не ответила: возможно, она запрещает скрипты или ее файла больше нет",
  "{n} more rows: narrow the search": "Еще {n} строк: уточни поиск",
  "Only the first {n} elements": "Только первые {n} элементов",
  "Select elements in the page; off, the page takes the clicks · V": "Выбирать элементы на странице; выключено, и клики получает сама страница · V",
  "Select": "Выбрать",
  // annotations and drawings on the page (owner 2026-10-07: «поверх картинки статичной, либо еще как»; 2026-10-09: comments are Annotations)
  "Annotation on an element: click it in the page · C": "Аннотация к элементу: кликни по нему на странице · C",
  "Annotation": "Аннотация",
  "Draw over the page · P": "Рисовать поверх страницы · P",
  "Draw": "Рисовать",
  "Click an element of the page to annotate it": "Кликни по элементу страницы, чтобы оставить аннотацию",
  // an annotation from the element tree (owner 2026-10-08): the row's button, its count, a dot on a folded row
  "Annotation on this element · C": "Аннотация к этому элементу · C",
  "New annotation on this element · C": "Новая аннотация к этому элементу · C",
  "{n} annotations: open": ["{n} аннотация: открыть", "{n} аннотации: открыть", "{n} аннотаций: открыть"],
  "Annotations inside": "Внутри есть аннотации",
  "The page did not say where this element is": "Страница не ответила, где этот элемент",
  "This element is gone from the page": "Этого элемента уже нет на странице",
  "Undo the last edit of the file · ⌘Z": "Отменить последнюю правку файла · ⌘Z",
  "Undo": "Отменить",
  "Redo · ⇧⌘Z": "Вернуть · ⇧⌘Z",
  "Redo": "Вернуть",
  "Reload the page": "Перезагрузить страницу",
  "Reload": "Обновить",
  "Open the page alone in a new tab, still sandboxed": "Открыть страницу отдельно в новой вкладке, тоже в песочнице",
  "Open": "Открыть",
  "Live view": "Живой просмотр",
  "The frame's live view: device sizes, its edges resize the page": "Живой просмотр фрейма: размеры устройств, края рамки меняют страницу",
  "Done · Esc": "Готово · Esc",
  "Done": "Готово",
  "Page": "Страница",
  "Viewport": "Вьюпорт",
  "<b>Click</b> an element in the page or the tree to edit it, <b>⇧</b> adds one": "<b>Клик</b> по элементу на странице или в дереве, чтобы его править, <b>⇧</b> добавляет еще один",
  "The page takes the clicks: <b>I</b> turns on Select to pick its elements, or pick one in the tree": "Клики получает страница: <b>I</b> включает «Выбрать», чтобы выбирать ее элементы, или выбери элемент в дереве",
  "Pinch zooms the board, after a click in the page the page; <b>Esc</b> undoes the click, <b>⌥</b> skips it": "Щипок приближает доску, а после клика по странице саму страницу. <b>Esc</b> отменяет клик, <b>⌥</b> обходится без него",
  "The page has the zoom · Esc to give it back": "Зум у страницы · Esc вернет его доске",
  // editing (0.2): the inspector's controls, typing in place, the reasons a thing can't be saved
  "Layout": "Раскладка",
  "Appearance": "Вид",
  "Fill": "Заливка",
  "Text": "Текст",
  "Stroke": "Обводка",
  "Colour": "Цвет",
  "Size": "Размер",
  "Weight": "Насыщенность",
  "Width": "Толщина",
  "Corners": "Углы",
  "Padding": "Отступы",
  "Gap": "Зазор",
  "Opacity": "Прозрачность",
  "This element": "Только этот",
  "Everywhere · {n}": "Везде · {n}",
  "From {tag}": "От {tag}",
  "{v} is declared outside this file": "{v} объявлена не в этом файле",
  "{v} is declared inside a rule Dev Studio doesn't write": "{v} объявлена в правиле, которое Dev Studio не правит",
  "<b>Double-click</b> the text or <b>Enter</b> to type it": "<b>Двойной клик</b> по тексту или <b>Enter</b>, чтобы его набрать",
  "<b>Reading</b> the file…": "<b>Читаю</b> файл…",
  "<b>Made by a script</b>, can't be saved: the file has no such element": "<b>Сделан скриптом</b>, сохранить нельзя: в файле такого элемента нет",
  "<b>Added by the browser</b>, can't be saved: the file has no such tag": "<b>Добавлен браузером</b>, сохранить нельзя: в файле такого тега нет",
  "<b>Can't save</b> this element: {why}": "<b>Нельзя сохранить</b> этот элемент: {why}",
  "<b>Can't save</b> this file: {why}": "<b>Нельзя сохранить</b> этот файл: {why}",
  "Only an element with nothing but text inside can be typed": "Набрать можно только элемент, внутри которого один текст",
  "This text can't be saved: it is not in the file": "Этот текст сохранить нельзя: его нет в файле",
  "The file can't be read": "Файл не читается",
  // П4 2026-10-10: ⌘↵ and Esc are Done, a refused write in words, a change made outside, History in the inspector's words
  "Done · ⌘↵ or Esc": "Готово · ⌘↵ или Esc",
  "the server did not write it": "сервер его не записал",
  "no connection to Hyimg": "нет связи с Hyimg",
  "The file had changed outside: your edit is in it, Reload shows the rest": "Файл меняли снаружи: ваша правка в нем, Reload покажет остальное",
  "Text size": "Размер текста",
  "Stroke width": "Толщина обводки",
  "Not saved: {why}": "Не записано: {why}",
  "Not saved: made by a script or the browser, {n}": "Не записано: сделано скриптом или браузером, {n}",
  "Can't undo: {why}": "Не отменить: {why}",
  "Can't redo: {why}": "Не повторить: {why}",
  "The file changed meanwhile: your edit was not saved, the page shows the file now": "Файл тем временем изменили: ваша правка не записана, страница показывает файл",
  "Box": "Блок",
  "Size": "Размер",
  "Position": "Положение",
  "Children": "Дочерние",
  "Styles": "Стили",
  "computed": "вычисленные",
  "Attributes": "Атрибуты",
  "none": "нет",
  "Dev Studio: this Hyimg shows no sandboxed pages, update it": "Dev Studio: этот Hyimg не показывает страницы в песочнице, обнови его",
  // round 15 (owner 2026-10-09): the right block's tabs, the crumbs, the LED, History; Edit mode («режим редактирования HTML»)
  "Inspector": "Инспектор",
  "History": "История",
  "Edit": "Правка",
  "Edit HTML": "Править HTML",
  "Edit the HTML, as in a browser's inspector · E": "Править HTML, как в инспекторе браузера · E",
  "Select {el}": "Выбрать {el}",
  "Writing to the file…": "Записываю в файл…",
  "Written to the file": "Записано в файл",
  "Edits go into the file as you make them": "Правки сразу записываются в файл",
  "Can't save this file: {why}": "Нельзя сохранить этот файл: {why}",
  "Opened": "Открыт",
  "<b>Edits</b> of this session show here, a click goes back to one": "Здесь видны <b>правки</b> этого сеанса, клик возвращает к любой",
  "Changed, written to the file": "Изменен, записано в файл",
  "everywhere": "везде",
  "Removed {a}": "Убран {a}",
  "Renamed {a}": "Переименован {a}",
  "Tag": "Тег",
  "Deleted": "Удален",
  "Not saved: it is not in the file": "Не записано: этого нет в файле",
  "Blur": "Размытие",
  "Only in a flex or grid box": "Только во flex- или grid-блоке",
  "The page's filter: {v}": "Фильтр страницы: {v}",
  "Light": "Light",
  "Regular": "Regular",
  "Medium": "Medium",
  "Semibold": "Semibold",
  "Bold": "Bold",
  "Extra bold": "Extra bold",
  "Not a tag name: {v}": "Это не имя тега: {v}",
  "Type attributes as name=\"value\"": "Атрибуты пишутся так: name=\"value\"",
  "New attributes": "Новые атрибуты",
  "Add attributes": "Добавить атрибуты",
  "Delete the element · ⌫": "Удалить элемент · ⌫",
  "Attribute name": "Имя атрибута",
  "Remove {a}": "Убрать {a}",
  "Not an attribute name: {v}": "Это не имя атрибута: {v}",
  "{n} elements": ["{n} элемент", "{n} элемента", "{n} элементов"],
};
const EN = {
  "{n} elements": ["{n} element", "{n} elements"],
  "{n} annotations: open": ["{n} annotation: open", "{n} annotations: open"],
};

const pre = d => Object.fromEntries(Object.entries(d).map(([k, v]) => [P + k, v]));
let added = false;
// t(key, vars) for this plugin: the board's T with the prefix, or English when the board has none
export function translator(HY) {
  if (HY.t && HY.strings) {
    if (!added) { HY.strings({ ru: pre(RU), en: pre(EN) }); added = true; }
    return (k, v) => HY.t(P + k, v);
  }
  return (k, v) => {
    let s = EN[k] !== undefined ? EN[k] : k;
    if (Array.isArray(s)) s = Number(v && v.n) === 1 ? s[0] : s[1];
    return v ? String(s).replace(/\{(\w+)\}/g, (m, x) => (x in v ? String(v[x]) : m)) : s;
  };
}
export { RU, EN };
