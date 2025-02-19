// Общие функции
function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.textContent = message;
    document.body.appendChild(notification);
    setTimeout(() => notification.remove(), 3000);
}

// Обработка ошибок
window.onerror = function(msg, url, line) {
    console.error(`Error: ${msg}\nURL: ${url}\nLine: ${line}`);
    showNotification('Произошла ошибка', 'error');
    return false;
}; 