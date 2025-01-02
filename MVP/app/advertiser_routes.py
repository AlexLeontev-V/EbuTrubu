# advertiser_routes.py

from quart import Blueprint, render_template, redirect, url_for, request, flash
import redis

advertiser_bp = Blueprint('advertiser', __name__)

# Подключение к Redis для хранения данных
r = redis.StrictRedis(host='localhost', port=6379, db=0, decode_responses=True)

@advertiser_bp.route('/advertiser_dashboard')
async def advertiser_dashboard():
    # Панель управления рекламодателя с общей статистикой кампаний
    return await render_template('advertiser_dashboard.html')

@advertiser_bp.route('/create_campaign', methods=['GET', 'POST'])
async def create_campaign():
    if request.method == 'POST':
        # Логика создания новой рекламной кампании
        campaign_data = await request.form
        flash('Кампания создана!', 'success')
        return redirect(url_for('advertiser.advertiser_dashboard'))
    return await render_template('create_campaign.html')

@advertiser_bp.route('/manage_balance', methods=['GET', 'POST'])
async def manage_balance():
    if request.method == 'POST':
        # Логика пополнения баланса
        balance_data = await request.form
        flash('Баланс пополнен', 'success')
        return redirect(url_for('advertiser.advertiser_dashboard'))
    return await render_template('manage_balance.html')
