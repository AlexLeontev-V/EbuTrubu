# streamer.py
from quart import Blueprint, render_template, redirect, url_for, request, flash

streamer_bp = Blueprint('streamer', __name__, template_folder='templates')

@streamer_bp.route('/streamer/dashboard')
async def dashboard():
    # Данные и логика для отображения панели стримера
    return await render_template('streamer_dashboard.html')

@streamer_bp.route('/streamer/start_stream', methods=['POST'])
async def start_stream():
    # Логика для начала трансляции
    flash("Трансляция начата!", "success")
    return redirect(url_for('streamer.dashboard'))
