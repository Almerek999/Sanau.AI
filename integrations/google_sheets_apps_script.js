/**
 * =========================================================================
 * Sanau.AI — Google Sheets Integration Webhook (Google Apps Script)
 * =========================================================================
 * 
 * Данный скрипт автоматически принимает данные о накладных от Sanau.AI
 * и добавляет строки в вашу Google Таблицу в реальном времени.
 * 
 * ИНСТРУКЦИЯ ПО УСТАНОВКЕ (Занимает 2 минуты):
 * 1. Откройте вашу Google Таблицу (sheets.google.com).
 * 2. В верхнем меню выберите: «Расширения» (Extensions) -> «Apps Script».
 * 3. Удалите весь существующий код в редакторе и вставьте данный скрипт.
 * 4. В правом верхнем углу нажмите синюю кнопку «Развернуть» (Deploy) -> «Новое развертывание» (New deployment).
 * 5. Нажмите на значок шестеренки рядом с «Выберите тип» и выберите «Веб-приложение» (Web app).
 * 6. Настройте параметры:
 *    - Описание: Sanau.AI Sync
 *    - Выполнять от имени: Я (ваш Google аккаунт)
 *    - У кого есть доступ: «Все» (Anyone)  <--- ВАЖНО, чтобы сервер Sanau.AI мог вносить данные!
 * 7. Нажмите «Развернуть» (Deploy) и подтвердите разрешения (Authorize access).
 * 8. Скопируйте полученный «URL веб-приложения» (https://script.google.com/macros/s/.../exec).
 * 9. Вставьте этот URL в Sanau.AI (в Mini App во вкладке «Сервисы» -> «Настроить» -> поле Google Sheets).
 * 10. Нажмите «Тест» для проверки!
 * =========================================================================
 */

function doPost(e) {
  try {
    if (!e || !e.postData || !e.postData.contents) {
      return ContentService.createTextOutput(JSON.stringify({
        status: "error",
        message: "Нет данных postData"
      })).setMimeType(ContentService.MimeType.JSON);
    }

    var data = JSON.parse(e.postData.contents);
    var ss = SpreadsheetApp.getActiveSpreadsheet();
    
    // Имя листа для вставки
    var targetSheetName = data.sheet_name || "Приемка товара";
    var sheet = ss.getSheetByName(targetSheetName);

    // Если листа нет — создаем его с красивыми заголовками
    if (!sheet) {
      sheet = ss.insertSheet(targetSheetName);
      var headers = [
        "Дата",
        "Номер накладной",
        "Поставщик",
        "Товар",
        "Количество",
        "Ед.изм",
        "Цена закупа (₸)",
        "Старая цена (₸)",
        "Статус цены",
        "Сумма (₸)",
        "Реком. розница (₸)"
      ];
      sheet.appendRow(headers);
      
      // Форматируем шапку: жирный шрифт, темный фон, белый текст
      var headerRange = sheet.getRange(1, 1, 1, headers.length);
      headerRange.setFontWeight("bold");
      headerRange.setBackground("#1e293b"); // slate-800
      headerRange.setFontColor("#ffffff");
      sheet.setFrozenRows(1);
    }

    // Обработка тестового пинга от Sanau.AI
    if (data.action === "ping") {
      return ContentService.createTextOutput(JSON.stringify({
        status: "success",
        message: "Google Sheets Webhook успешно подключен к Sanau.AI!"
      })).setMimeType(ContentService.MimeType.JSON);
    }

    // Вставка строк накладной
    if (data.rows && Array.isArray(data.rows) && data.rows.length > 0) {
      data.rows.forEach(function(row) {
        var rowData = [
          row["Дата"] || new Date().toLocaleDateString("ru-RU"),
          row["Номер накладной"] || "б/н",
          row["Поставщик"] || "—",
          row["Товар"] || "—",
          row["Количество"] || 1,
          row["Ед.изм"] || "шт",
          row["Цена закупа (₸)"] || 0,
          row["Старая цена (₸)"] || "—",
          row["Статус цены"] || "ОК",
          row["Сумма (₸)"] || 0,
          row["Реком. розница (₸)"] || "—"
        ];
        sheet.appendRow(rowData);
        
        // Подсвечиваем подорожание красным цветом
        var lastRow = sheet.getLastRow();
        if (row["Статус цены"] && row["Статус цены"].indexOf("ВНИМАНИЕ") !== -1) {
          sheet.getRange(lastRow, 9).setBackground("#fee2e2").setFontColor("#b91c1c").setFontWeight("bold");
        }
      });

      return ContentService.createTextOutput(JSON.stringify({
        status: "success",
        message: "Добавлено " + data.rows.length + " строк",
        count: data.rows.length
      })).setMimeType(ContentService.MimeType.JSON);
    }

    return ContentService.createTextOutput(JSON.stringify({
      status: "warning",
      message: "Массив rows пуст"
    })).setMimeType(ContentService.MimeType.JSON);

  } catch (error) {
    return ContentService.createTextOutput(JSON.stringify({
      status: "error",
      error: error.toString()
    })).setMimeType(ContentService.MimeType.JSON);
  }
}

// Тестовая функция для ручной проверки в редакторе Apps Script
function testScript() {
  var mockEvent = {
    postData: {
      contents: JSON.stringify({
        action: "insert_rows",
        sheet_name: "Приемка товара",
        rows: [
          {
            "Дата": "16.10.2026",
            "Номер накладной": "ТЕСТ-001",
            "Поставщик": "ТОО Родина",
            "Товар": "Молоко 'Родина' 3.2% 1л",
            "Количество": 20,
            "Ед.изм": "шт",
            "Цена закупа (₸)": 440,
            "Старая цена (₸)": 390,
            "Статус цены": "🚨 ВНИМАНИЕ: +12.8%",
            "Сумма (₸)": 8800,
            "Реком. розница (₸)": 570
          }
        ]
      })
    }
  };
  var res = doPost(mockEvent);
  Logger.log(res.getContent());
}
