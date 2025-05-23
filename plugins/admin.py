from pyrogram import Client, filters
from pyrogram.types import Message
from models import User, QuizAttempt, UserAnswer
from peewee import fn
import datetime

# List of admin user IDs (Telegram IDs of users who can access admin commands)
ADMIN_USER_IDS = [652429947]

# Admin filter - only allow commands from admin users
def admin_filter(_, __, message):
    return message.from_user and message.from_user.id in ADMIN_USER_IDS

admin_only = filters.create(admin_filter)

@Client.on_message(filters.command("admin") & admin_only)
async def admin_command(client: Client, message: Message):
    """Show admin commands help"""
    await message.reply_text(
        "🔐 **Admin Commands**\n\n"
        "/admin - Show this help message\n"
        "/users - Show total user count and recent users\n"
        "/user_stats <user_id> - Show detailed stats for a specific user\n"
        "/global_stats - Show global statistics for the bot\n"
        "/active_users - Show most active users by quiz count\n"
        "/top_scores - Show users with highest scores\n"
        "/cleanup - Database maintenance and cleanup operations"
    )

@Client.on_message(filters.command("users") & admin_only)
async def users_command(client: Client, message: Message):
    """Show total user count and recent users"""
    total_users = User.select().count()
    recent_users = User.select().order_by(User.joined_date.desc()).limit(10)
    
    user_list = "\n".join(
        f"{i+1}. {user.first_name} {user.last_name or ''} (@{user.username or 'No username'}) - "
        f"ID: {user.user_id} - Joined: {user.joined_date.strftime('%Y-%m-%d')}"
        for i, user in enumerate(recent_users)
    )
    
    await message.reply_text(
        f"👥 **User Statistics**\n\n"
        f"Total registered users: {total_users}\n\n"
        f"**Most recent users:**\n{user_list}"
    )

@Client.on_message(filters.command("user_stats") & admin_only)
async def user_stats_command(client: Client, message: Message):
    """Show detailed stats for a specific user"""
    # Check if user ID is provided
    command_parts = message.text.split()
    if len(command_parts) < 2:
        await message.reply_text("Please provide a user ID. Example: /user_stats 123456789")
        return
    
    try:
        user_id = int(command_parts[1])
    except ValueError:
        await message.reply_text("Invalid user ID. Please provide a numeric ID.")
        return
    
    # Get user
    try:
        user = User.get(User.user_id == user_id)
    except User.DoesNotExist:
        await message.reply_text(f"User with ID {user_id} not found.")
        return
    
    # Get quiz attempts
    quiz_attempts = QuizAttempt.select().where(QuizAttempt.user == user)
    completed_quizzes = quiz_attempts.where(QuizAttempt.end_time.is_null(False))
    
    # Calculate statistics
    total_attempts = quiz_attempts.count()
    completed_count = completed_quizzes.count()
    
    if completed_count > 0:
        avg_score = sum(q.score for q in completed_quizzes) / completed_count
        best_score = max((q.score for q in completed_quizzes), default=0)
        total_questions_answered = UserAnswer.select().join(QuizAttempt).where(QuizAttempt.user == user).count()
        correct_answers = UserAnswer.select().join(QuizAttempt).where(
            (QuizAttempt.user == user) & (UserAnswer.is_correct == True)
        ).count()
        accuracy = (correct_answers / total_questions_answered * 100) if total_questions_answered > 0 else 0
    else:
        avg_score = 0
        best_score = 0
        total_questions_answered = 0
        correct_answers = 0
        accuracy = 0
    
    # Get recent activity
    last_activity = quiz_attempts.order_by(QuizAttempt.start_time.desc()).first()
    last_activity_time = last_activity.start_time if last_activity else "Never"
    
    await message.reply_text(
        f"📊 **User Details**\n\n"
        f"User: {user.first_name} {user.last_name or ''}\n"
        f"Username: @{user.username or 'None'}\n"
        f"User ID: {user.user_id}\n"
        f"Joined: {user.joined_date.strftime('%Y-%m-%d %H:%M')}\n\n"
        f"**Quiz Statistics:**\n"
        f"Total quiz attempts: {total_attempts}\n"
        f"Completed quizzes: {completed_count}\n"
        f"Average score: {avg_score:.1f}\n"
        f"Best score: {best_score}\n"
        f"Questions answered: {total_questions_answered}\n"
        f"Correct answers: {correct_answers}\n"
        f"Accuracy: {accuracy:.1f}%\n\n"
        f"Last activity: {last_activity_time}"
    )

@Client.on_message(filters.command("global_stats") & admin_only)
async def global_stats_command(client: Client, message: Message):
    """Show global statistics for the bot"""
    total_users = User.select().count()
    total_quizzes = QuizAttempt.select().count()
    completed_quizzes = QuizAttempt.select().where(QuizAttempt.end_time.is_null(False)).count()
    total_questions = UserAnswer.select().count()
    correct_answers = UserAnswer.select().where(UserAnswer.is_correct == True).count()
    
    # Calculate global accuracy
    accuracy = (correct_answers / total_questions * 100) if total_questions > 0 else 0
    
    # Get average score
    avg_score_query = QuizAttempt.select(fn.AVG(QuizAttempt.score)).where(QuizAttempt.end_time.is_null(False))
    avg_score = avg_score_query.scalar() or 0
    
    # Get users registered in the last 7 days
    week_ago = datetime.datetime.now() - datetime.timedelta(days=7)
    new_users = User.select().where(User.joined_date >= week_ago).count()
    
    # Get quizzes taken in the last 7 days
    recent_quizzes = QuizAttempt.select().where(QuizAttempt.start_time >= week_ago).count()
    
    await message.reply_text(
        f"📈 **Global Statistics**\n\n"
        f"**User Stats:**\n"
        f"Total users: {total_users}\n"
        f"New users (last 7 days): {new_users}\n\n"
        f"**Quiz Stats:**\n"
        f"Total quizzes started: {total_quizzes}\n"
        f"Completed quizzes: {completed_quizzes}\n"
        f"Quizzes taken (last 7 days): {recent_quizzes}\n"
        f"Average score: {avg_score:.1f}\n\n"
        f"**Question Stats:**\n"
        f"Total questions answered: {total_questions}\n"
        f"Correct answers: {correct_answers}\n"
        f"Global accuracy: {accuracy:.1f}%"
    )

@Client.on_message(filters.command("active_users") & admin_only)
async def active_users_command(client: Client, message: Message):
    """Show most active users by quiz count"""
    # Get users with the most quiz attempts
    query = (
        User
        .select(User, fn.COUNT(QuizAttempt.id).alias('quiz_count'))
        .join(QuizAttempt)
        .group_by(User.id)
        .order_by(fn.COUNT(QuizAttempt.id).desc())
        .limit(10)
    )
    
    if not query.exists():
        await message.reply_text("No quiz attempts recorded yet.")
        return
    
    user_list = "\n".join(
        f"{i+1}. {user.first_name} {user.last_name or ''} (@{user.username or 'No username'}) - "
        f"{user.quiz_count} quizzes"
        for i, user in enumerate(query)
    )
    
    await message.reply_text(
        f"🏆 **Most Active Users**\n\n{user_list}"
    )

@Client.on_message(filters.command("top_scores") & admin_only)
async def top_scores_command(client: Client, message: Message):
    """Show users with highest scores"""
    # Get top quiz scores
    top_scores = (
        QuizAttempt
        .select(QuizAttempt, User)
        .join(User)
        .where(QuizAttempt.end_time.is_null(False))
        .order_by(QuizAttempt.score.desc())
        .limit(10)
    )
    
    if not top_scores.exists():
        await message.reply_text("No completed quizzes yet.")
        return
    
    score_list = "\n".join(
        f"{i+1}. {attempt.user.first_name} {attempt.user.last_name or ''} - "
        f"Score: {attempt.score}/{attempt.total_questions} "
        f"({attempt.score/attempt.total_questions*100:.1f}%)"
        for i, attempt in enumerate(top_scores)
    )
    
    await message.reply_text(
        f"🥇 **Top Quiz Scores**\n\n{score_list}"
    )

@Client.on_message(filters.command("cleanup") & admin_only)
async def cleanup_command(client: Client, message: Message):
    """Handle database cleanup operations"""
    command_parts = message.text.split()
    
    # Show help if no arguments provided
    if len(command_parts) == 1:
        await message.reply_text(
            "🧹 **Database Cleanup**\n\n"
            "Usage:\n"
            "/cleanup help - Show this help message\n"
            "/cleanup stats - Show cleanup statistics\n"
            "/cleanup inactive_users <days> - Delete users inactive for X days\n"
            "/cleanup old_quizzes <days> - Delete quiz attempts older than X days\n"
            "/cleanup incomplete_quizzes - Delete quiz attempts that were never completed\n"
            "/cleanup all <days> - Full cleanup of data older than X days\n\n"
            "⚠️ **Warning**: These operations permanently delete data and cannot be undone."
        )
        return
    
    action = command_parts[1].lower()
    
    # Show help
    if action == "help":
        await message.reply_text(
            "🧹 **Database Cleanup**\n\n"
            "Usage:\n"
            "/cleanup help - Show this help message\n"
            "/cleanup stats - Show cleanup statistics\n"
            "/cleanup inactive_users <days> - Delete users inactive for X days\n"
            "/cleanup old_quizzes <days> - Delete quiz attempts older than X days\n"
            "/cleanup incomplete_quizzes - Delete quiz attempts that were never completed\n"
            "/cleanup all <days> - Full cleanup of data older than X days\n\n"
            "⚠️ **Warning**: These operations permanently delete data and cannot be undone."
        )
    
    # Show cleanup statistics
    elif action == "stats":
        # Calculate statistics for potential cleanup
        total_users = User.select().count()
        total_quizzes = QuizAttempt.select().count()
        total_answers = UserAnswer.select().count()
        
        # Incomplete quizzes
        incomplete_quizzes = QuizAttempt.select().where(QuizAttempt.end_time.is_null(True)).count()
        
        # Old quizzes (> 30 days)
        thirty_days_ago = datetime.datetime.now() - datetime.timedelta(days=30)
        old_quizzes = QuizAttempt.select().where(QuizAttempt.start_time < thirty_days_ago).count()
        
        # Inactive users (no quiz in last 30 days)
        active_user_ids = QuizAttempt.select(QuizAttempt.user).where(QuizAttempt.start_time >= thirty_days_ago).distinct()
        inactive_users = User.select().where(User.id.not_in(active_user_ids)).count()
        
        await message.reply_text(
            f"📊 **Cleanup Statistics**\n\n"
            f"Total database records:\n"
            f"- Users: {total_users}\n"
            f"- Quiz attempts: {total_quizzes}\n"
            f"- User answers: {total_answers}\n\n"
            f"Potential cleanup:\n"
            f"- Incomplete quizzes: {incomplete_quizzes}\n"
            f"- Quizzes older than 30 days: {old_quizzes}\n"
            f"- Users inactive for 30+ days: {inactive_users}\n\n"
            f"Use specific cleanup commands to remove these records."
        )
    
    # Delete inactive users
    elif action == "inactive_users":
        if len(command_parts) < 3:
            await message.reply_text("Please specify the number of days. Example: /cleanup inactive_users 30")
            return
        
        try:
            days = int(command_parts[2])
            if days < 1:
                await message.reply_text("Days must be a positive number.")
                return
        except ValueError:
            await message.reply_text("Invalid number of days. Please provide a valid number.")
            return
        
        # Find inactive users
        cutoff_date = datetime.datetime.now() - datetime.timedelta(days=days)
        active_user_ids = QuizAttempt.select(QuizAttempt.user).where(QuizAttempt.start_time >= cutoff_date).distinct()
        inactive_users = User.select().where(User.id.not_in(active_user_ids))
        inactive_count = inactive_users.count()
        
        # Confirmation message
        confirm_msg = await message.reply_text(
            f"⚠️ **Confirmation Required**\n\n"
            f"You are about to delete {inactive_count} users who have been inactive for {days}+ days.\n"
            f"This will also delete all their quiz attempts and answers.\n\n"
            f"Reply with 'CONFIRM' to proceed or 'CANCEL' to abort."
        )
        
        # Wait for confirmation
        @Client.on_message(filters.reply & filters.text & filters.user(message.from_user.id))
        async def confirm_inactive_deletion(client, confirm_message):
            if confirm_message.reply_to_message.id != confirm_msg.id:
                return
            
            if confirm_message.text.upper() == "CONFIRM":
                # Delete inactive users and their data
                deleted_count = 0
                for user in inactive_users:
                    # Get all quiz attempts for this user
                    user_attempts = QuizAttempt.select().where(QuizAttempt.user == user.id)
                    
                    # Delete all answers for these attempts
                    for attempt in user_attempts:
                        UserAnswer.delete().where(UserAnswer.quiz_attempt == attempt.id).execute()
                    
                    # Delete all quiz attempts
                    QuizAttempt.delete().where(QuizAttempt.user == user.id).execute()
                    
                    # Delete the user
                    user.delete_instance()
                    deleted_count += 1
                
                await confirm_message.reply_text(f"✅ Successfully deleted {deleted_count} inactive users and all their data.")
            elif confirm_message.text.upper() == "CANCEL":
                await confirm_message.reply_text("Operation cancelled.")
            else:
                await confirm_message.reply_text("Invalid response. Operation cancelled.")
            
            # Remove the handler
            client.remove_handler(confirm_inactive_deletion)
    
    # Delete old quizzes
    elif action == "old_quizzes":
        if len(command_parts) < 3:
            await message.reply_text("Please specify the number of days. Example: /cleanup old_quizzes 30")
            return
        
        try:
            days = int(command_parts[2])
            if days < 1:
                await message.reply_text("Days must be a positive number.")
                return
        except ValueError:
            await message.reply_text("Invalid number of days. Please provide a valid number.")
            return
        
        # Find old quizzes
        cutoff_date = datetime.datetime.now() - datetime.timedelta(days=days)
        old_quizzes = QuizAttempt.select().where(QuizAttempt.start_time < cutoff_date)
        old_count = old_quizzes.count()
        
        # Confirmation message
        confirm_msg = await message.reply_text(
            f"⚠️ **Confirmation Required**\n\n"
            f"You are about to delete {old_count} quiz attempts that are older than {days} days.\n"
            f"This will also delete all answers associated with these quizzes.\n\n"
            f"Reply with 'CONFIRM' to proceed or 'CANCEL' to abort."
        )
        
        # Wait for confirmation
        @Client.on_message(filters.reply & filters.text & filters.user(message.from_user.id))
        async def confirm_old_quizzes_deletion(client, confirm_message):
            if confirm_message.reply_to_message.id != confirm_msg.id:
                return
            
            if confirm_message.text.upper() == "CONFIRM":
                # Delete old quizzes and their answers
                deleted_count = 0
                for quiz in old_quizzes:
                    # Delete all answers for this quiz
                    UserAnswer.delete().where(UserAnswer.quiz_attempt == quiz.id).execute()
                    
                    # Delete the quiz attempt
                    quiz.delete_instance()
                    deleted_count += 1
                
                await confirm_message.reply_text(f"✅ Successfully deleted {deleted_count} old quiz attempts and all their answers.")
            elif confirm_message.text.upper() == "CANCEL":
                await confirm_message.reply_text("Operation cancelled.")
            else:
                await confirm_message.reply_text("Invalid response. Operation cancelled.")
            
            # Remove the handler
            client.remove_handler(confirm_old_quizzes_deletion)
    
    # Delete incomplete quizzes
    elif action == "incomplete_quizzes":
        # Find incomplete quizzes
        incomplete_quizzes = QuizAttempt.select().where(QuizAttempt.end_time.is_null(True))
        incomplete_count = incomplete_quizzes.count()
        
        if incomplete_count == 0:
            await message.reply_text("There are no incomplete quizzes to delete.")
            return
        
        # Confirmation message
        confirm_msg = await message.reply_text(
            f"⚠️ **Confirmation Required**\n\n"
            f"You are about to delete {incomplete_count} incomplete quiz attempts.\n"
            f"This will also delete all answers associated with these quizzes.\n\n"
            f"Reply with 'CONFIRM' to proceed or 'CANCEL' to abort."
        )
        
        # Wait for confirmation
        @Client.on_message(filters.reply & filters.text & filters.user(message.from_user.id))
        async def confirm_incomplete_deletion(client, confirm_message):
            if confirm_message.reply_to_message.id != confirm_msg.id:
                return
            
            if confirm_message.text.upper() == "CONFIRM":
                # Delete incomplete quizzes and their answers
                deleted_count = 0
                for quiz in incomplete_quizzes:
                    # Delete all answers for this quiz
                    UserAnswer.delete().where(UserAnswer.quiz_attempt == quiz.id).execute()
                    
                    # Delete the quiz attempt
                    quiz.delete_instance()
                    deleted_count += 1
                
                await confirm_message.reply_text(f"✅ Successfully deleted {deleted_count} incomplete quiz attempts and all their answers.")
            elif confirm_message.text.upper() == "CANCEL":
                await confirm_message.reply_text("Operation cancelled.")
            else:
                await confirm_message.reply_text("Invalid response. Operation cancelled.")
            
            # Remove the handler
            client.remove_handler(confirm_incomplete_deletion)
    
    # Full cleanup
    elif action == "all":
        if len(command_parts) < 3:
            await message.reply_text("Please specify the number of days. Example: /cleanup all 30")
            return
        
        try:
            days = int(command_parts[2])
            if days < 1:
                await message.reply_text("Days must be a positive number.")
                return
        except ValueError:
            await message.reply_text("Invalid number of days. Please provide a valid number.")
            return
        
        # Calculate statistics for cleanup
        cutoff_date = datetime.datetime.now() - datetime.timedelta(days=days)
        
        # Find old quizzes
        old_quizzes = QuizAttempt.select().where(QuizAttempt.start_time < cutoff_date)
        old_count = old_quizzes.count()
        
        # Find incomplete quizzes
        incomplete_quizzes = QuizAttempt.select().where(QuizAttempt.end_time.is_null(True))
        incomplete_count = incomplete_quizzes.count()
        
        # Find inactive users
        active_user_ids = QuizAttempt.select(QuizAttempt.user).where(QuizAttempt.start_time >= cutoff_date).distinct()
        inactive_users = User.select().where(User.id.not_in(active_user_ids))
        inactive_count = inactive_users.count()
        
        # Confirmation message
        confirm_msg = await message.reply_text(
            f"⚠️ **Full Database Cleanup Confirmation**\n\n"
            f"You are about to perform a full cleanup of data older than {days} days:\n"
            f"- {inactive_count} inactive users\n"
            f"- {old_count} old quiz attempts\n"
            f"- {incomplete_count} incomplete quiz attempts\n\n"
            f"This is a destructive operation and cannot be undone.\n\n"
            f"Reply with 'CONFIRM' to proceed or 'CANCEL' to abort."
        )
        
        # Wait for confirmation
        @Client.on_message(filters.reply & filters.text & filters.user(message.from_user.id))
        async def confirm_full_cleanup(client, confirm_message):
            if confirm_message.reply_to_message.id != confirm_msg.id:
                return
            
            if confirm_message.text.upper() == "CONFIRM":
                status_msg = await confirm_message.reply_text("Cleanup in progress... This may take a while.")
                
                # 1. Delete old and incomplete quizzes first
                quizzes_to_delete = list(old_quizzes) + list(incomplete_quizzes)
                quiz_ids = [q.id for q in quizzes_to_delete]
                
                # Delete answers for these quizzes
                answers_deleted = UserAnswer.delete().where(UserAnswer.quiz_attempt.in_(quiz_ids)).execute()
                
                # Delete the quizzes
                quizzes_deleted = QuizAttempt.delete().where(QuizAttempt.id.in_(quiz_ids)).execute()
                
                # 2. Delete inactive users
                users_deleted = 0
                for user in inactive_users:
                    # Get remaining quiz attempts for this user
                    remaining_attempts = QuizAttempt.select().where(QuizAttempt.user == user.id)
                    
                    # Delete all answers for these attempts
                    for attempt in remaining_attempts:
                        UserAnswer.delete().where(UserAnswer.quiz_attempt == attempt.id).execute()
                    
                    # Delete all quiz attempts
                    QuizAttempt.delete().where(QuizAttempt.user == user.id).execute()
                    
                    # Delete the user
                    user.delete_instance()
                    users_deleted += 1
                
                await status_msg.edit_text(
                    f"✅ **Cleanup Complete**\n\n"
                    f"Deleted:\n"
                    f"- {users_deleted} inactive users\n"
                    f"- {quizzes_deleted} quiz attempts\n"
                    f"- {answers_deleted} user answers\n\n"
                    f"Database has been successfully cleaned up."
                )
            elif confirm_message.text.upper() == "CANCEL":
                await confirm_message.reply_text("Operation cancelled.")
            else:
                await confirm_message.reply_text("Invalid response. Operation cancelled.")
            
            # Remove the handler
            client.remove_handler(confirm_full_cleanup)
    
    else:
        await message.reply_text(f"Unknown action: {action}\nUse /cleanup help to see available commands.")

# Update the admin help command to include the cleanup command
@Client.on_message(filters.command("admin") & admin_only)
async def admin_command(client: Client, message: Message):
    """Show admin commands help"""
    await message.reply_text(
        "🔐 **Admin Commands**\n\n"
        "/admin - Show this help message\n"
        "/users - Show total user count and recent users\n"
        "/user_stats <user_id> - Show detailed stats for a specific user\n"
        "/global_stats - Show global statistics for the bot\n"
        "/active_users - Show most active users by quiz count\n"
        "/top_scores - Show users with highest scores\n"
        "/cleanup - Database maintenance and cleanup operations"
    )