from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from app.models.notification import Notification

bp = Blueprint('notifications', __name__, url_prefix='/notifications')

@bp.route('/')
@login_required
def index():
    """View all notifications"""
    notifications = Notification.get_by_user(current_user.id)
    unread_count = Notification.get_unread_count(current_user.id)
    
    return render_template('notifications/index.html',
                         notifications=notifications,
                         unread_count=unread_count)

@bp.route('/unread')
@login_required
def unread():
    """Get unread notifications (AJAX)"""
    notifications = Notification.get_by_user(current_user.id, unread_only=True, limit=10)
    unread_count = Notification.get_unread_count(current_user.id)
    
    return jsonify({
        'count': unread_count,
        'notifications': [{
            'id': n.id,
            'title': n.title,
            'message': n.message,
            'type': n.type,
            'link': n.link,
            'created_at': n.created_at
        } for n in notifications]
    })

@bp.route('/<int:notification_id>/read', methods=['POST'])
@login_required
def mark_read(notification_id):
    """Mark a notification as read"""
    success, error = Notification.mark_as_read(notification_id, current_user.id)
    
    if success:
        return jsonify({'success': True})
    else:
        return jsonify({'success': False, 'message': error}), 400

@bp.route('/mark-all-read', methods=['POST'])
@login_required
def mark_all_read():
    """Mark all notifications as read"""
    success, error = Notification.mark_all_as_read(current_user.id)
    
    if success:
        return jsonify({'success': True})
    else:
        return jsonify({'success': False, 'message': error}), 400

@bp.route('/<int:notification_id>/delete', methods=['POST'])
@login_required
def delete(notification_id):
    """Delete a notification"""
    success, error = Notification.delete_notification(notification_id, current_user.id)
    
    if success:
        return jsonify({'success': True})
    else:
        return jsonify({'success': False, 'message': error}), 400

@bp.route('/delete-all-read', methods=['POST'])
@login_required
def delete_all_read():
    """Delete all read notifications"""
    success, error = Notification.delete_all_read(current_user.id)
    
    if success:
        return jsonify({'success': True})
    else:
        return jsonify({'success': False, 'message': error}), 400
