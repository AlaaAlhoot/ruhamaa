// مساعد تصدير Excel مع Modal
function showExportModal(label, url) {
    document.getElementById('exportRegionLabel').textContent = label;
    const modal = new bootstrap.Modal(document.getElementById('exportModal'));
    modal.show();

    setTimeout(() => {
        window.location.href = url;
        setTimeout(() => modal.hide(), 2000);
    }, 800);
}
```

---

## الآن تحتاج تحميل هذه الملفات يدوياً

### Bootstrap RTL
```
https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.rtl.min.css
https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js
```
احفظهما في `static/bootstrap/`

### خط Cairo
```
https://fonts.google.com/specimen/Cairo