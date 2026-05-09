// ==================== CSRF ====================
function getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(';').shift();
    return '';
}
const CSRF = getCookie('csrftoken');


// ==================== Confirm Actions ====================
function confirmAction(msg, callback) {
    if (confirm(msg)) callback();
}


// ==================== Alerts ====================
function showAlert(msg, type = 'success', duration = 3000) {
    const div = document.createElement('div');
    div.className = `alert alert-${type} position-fixed top-0 start-50 translate-middle-x mt-3`;
    div.style.zIndex = '9999';
    div.textContent = msg;
    document.body.appendChild(div);
    setTimeout(() => div.remove(), duration);
}