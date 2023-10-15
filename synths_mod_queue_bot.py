import datetime
import os

import praw

DEFAULT_SUBREDDIT_NAME = 'synthesizers'

AUTO_APPROVE_SCORE = 100
AUTO_APPROVE_NUM_REPORTS_THRESHOLD = 3
AUTO_REMOVE_MINS = 60 * 3
AUTO_REMOVE_NUM_REPORTS = 1
AUTO_REMOVE_SCORE = 0
AUTO_REMOVE_UPVOTE_RATIO = 0.5

APPROVED_LINK_DOMAINS = [
    "https://a.co/"
]


class SynthsModQueueBot:
    def __init__(self, subreddit_name=DEFAULT_SUBREDDIT_NAME, dry_run=False, reddit=None):
        self.dry_run = dry_run

        self.reddit = reddit if reddit else praw.Reddit('SynthsModQueueBot')
        self.mod = self.reddit.subreddit(subreddit_name).mod

    def scan(self):
        for item in self.mod.modqueue(limit=None):
            if isinstance(item, praw.models.Submission):
                self.process_submission(item)
            elif isinstance(item, praw.models.Comment):
                self.process_comment(item)

    def process_submission(self, submission):
        submission_mins = self.submission_age_mins(submission)

        if ((submission.score >= AUTO_APPROVE_SCORE
                and submission.num_reports < AUTO_APPROVE_NUM_REPORTS_THRESHOLD)):
            self.approve_item(submission)
        elif ((self.calc_user_reports_count(submission) >= AUTO_REMOVE_NUM_REPORTS
                and submission.score <= AUTO_REMOVE_SCORE
                and submission.upvote_ratio < AUTO_REMOVE_UPVOTE_RATIO
                and submission_mins >= AUTO_REMOVE_MINS)):
            self.remove_item(submission, "Autoremoved due to user reports and low upvote ratio.")

    def process_comment(self, comment):
        self.process_spam_filtered_comment(comment)

    def process_spam_filtered_comment(self, comment):
        for domain in APPROVED_LINK_DOMAINS:
            if domain in comment.body:
                self.approve_item(comment)

    def approve_item(self, item):
        if not self.dry_run:
            item.mod.approve()
        self.print_message("Approved", item)

    def remove_item(self, item, mod_note=None):
        if not self.dry_run:
            item.mod.remove(mod_note=mod_note)
        self.print_message("Removed", item)

    def calc_user_reports_count(self, obj):
        count = len(obj.user_reports)

        if hasattr(obj, 'user_reports_dismissed'):
            count += len(obj.user_reports_dismissed)

        return count

    @ staticmethod
    def submission_age_mins(submission):
        now = datetime.datetime.now()
        created = datetime.datetime.fromtimestamp(submission.created_utc)
        age = now - created
        return age.total_seconds() / 60

    def print_message(self, message, item):
        is_dry_run = '*' if self.dry_run is True else ''
        name = type(self).__name__
        now = datetime.datetime.now()
        print(f'{is_dry_run}[{name}][{now}] {message}: ({item.id})')


def main():
    subreddit_name = os.environ['subreddit_name'] if 'subreddit_name' in os.environ else DEFAULT_SUBREDDIT_NAME
    dry_run = os.environ['dry_run'] == 'True' if 'dry_run' in os.environ else False
    bot = SynthsModQueueBot(subreddit_name=subreddit_name, dry_run=dry_run)
    bot.scan()


if __name__ == '__main__':
    main()
