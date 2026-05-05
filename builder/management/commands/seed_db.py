from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from user.models import UserProfile
from builder.models import Form, Submission, DraftSubmission


LOAN_SCHEMA = {
    "steps": [
        {
            "id": "personal_info",
            "title": "Personal Information",
            "fields": [
                {
                    "id": "full_name",
                    "type": "text",
                    "label": "Full Name",
                    "required": True,
                    "placeholder": "Enter your full name"
                },
                {
                    "id": "email",
                    "type": "email",
                    "label": "Email Address",
                    "required": True,
                    "placeholder": "Enter your email"
                },
                {
                    "id": "employment_status",
                    "type": "select",
                    "label": "Employment Status",
                    "required": True,
                    "options": ["employed", "self-employed", "unemployed"]
                }
            ]
        },
        {
            "id": "financial_info",
            "title": "Financial Information",
            "fields": [
                {
                    "id": "salary",
                    "type": "number",
                    "label": "Monthly Salary",
                    "required": True,
                    "validations": [
                        {"type": "min", "value": 10000}
                    ],
                    "visibility": {
                        "condition": {
                            "field": "employment_status",
                            "operator": "==",
                            "value": "employed"
                        }
                    }
                },
                {
                    "id": "business_revenue",
                    "type": "number",
                    "label": "Monthly Business Revenue",
                    "required": True,
                    "validations": [
                        {"type": "min", "value": 5000}
                    ],
                    "visibility": {
                        "condition": {
                            "field": "employment_status",
                            "operator": "==",
                            "value": "self-employed"
                        }
                    }
                },
                {
                    "id": "loan_amount",
                    "type": "number",
                    "label": "Loan Amount Requested",
                    "required": True,
                    "validations": [
                        {"type": "min", "value": 1000},
                        {"type": "max", "value": 500000}
                    ]
                },
                {
                    "id": "loan_purpose",
                    "type": "select",
                    "label": "Loan Purpose",
                    "required": True,
                    "options": ["home", "vehicle", "education", "business", "personal"]
                }
            ]
        }
    ],
    "navigation": [
        {
            "from_step": "personal_info",
            "to_step": "financial_info"
        }
    ],
    "rules": [
        {
            "if": {"field": "salary", "operator": ">", "value": 100000},
            "then": {"action": "set_value", "field": "status", "value": "pre-approved"}
        },
        {
            "if": {"field": "salary", "operator": "<=", "value": 100000},
            "then": {"action": "set_status", "value": "under_review"}
        },
        {
            "if": {"field": "loan_purpose", "operator": "==", "value": "education"},
            "then": {"action": "tag", "value": "education_loan"}
        }
    ],
    "settings": {}
}

CONTACT_SCHEMA = {
    "steps": [
        {
            "id": "contact",
            "title": "Contact Us",
            "fields": [
                {
                    "id": "name",
                    "type": "text",
                    "label": "Your Name",
                    "required": True,
                    "placeholder": "Enter your name"
                },
                {
                    "id": "email",
                    "type": "email",
                    "label": "Email",
                    "required": True,
                    "placeholder": "Enter your email"
                },
                {
                    "id": "subject",
                    "type": "select",
                    "label": "Subject",
                    "required": True,
                    "options": ["support", "sales", "billing", "other"]
                },
                {
                    "id": "message",
                    "type": "textarea",
                    "label": "Message",
                    "required": True,
                    "placeholder": "Write your message here",
                    "validations": [
                        {"type": "min", "value": 20}
                    ]
                }
            ]
        }
    ],
    "navigation": [],
    "rules": [
        {
            "if": {"field": "subject", "operator": "==", "value": "support"},
            "then": {"action": "tag", "value": "needs_support"}
        }
    ],
    "settings": {}
}


class Command(BaseCommand):
    help = 'Seed the database with test users, forms, submissions, and drafts.'

    def handle(self, *args, **kwargs):
        self._create_users()
        self._create_forms()
        self._create_submissions()
        self._create_draft()
        self.stdout.write(self.style.SUCCESS('\nDatabase seeded successfully.'))

    # ------------------------------------------------------------------

    def _create_users(self):
        self.stdout.write('Creating users...')

        admin, created = User.objects.get_or_create(username='admin')
        if created:
            admin.set_password('admin123')
            admin.is_staff = True
            admin.is_superuser = True
            admin.email = 'admin@example.com'
            admin.save()
            UserProfile.objects.get_or_create(user=admin)
            self.stdout.write(f'  Created superuser  → username: admin  password: admin123')
        else:
            self.stdout.write(f'  admin already exists, skipped.')

        testuser, created = User.objects.get_or_create(username='testuser')
        if created:
            testuser.set_password('testpass123')
            testuser.first_name = 'Test'
            testuser.last_name = 'User'
            testuser.email = 'test@example.com'
            testuser.save()
            UserProfile.objects.get_or_create(user=testuser)
            self.stdout.write(f'  Created user       → username: testuser  password: testpass123')
        else:
            self.stdout.write(f'  testuser already exists, skipped.')

        self.testuser = User.objects.get(username='testuser')

    def _create_forms(self):
        self.stdout.write('Creating forms...')

        self.loan_form, created = Form.objects.get_or_create(
            owner=self.testuser,
            name='Loan Application',
            defaults={
                'version': 1,
                'schema': LOAN_SCHEMA,
                'is_published': True,
            }
        )
        status = 'Created' if created else 'Already exists'
        self.stdout.write(f'  {status} → Form id={self.loan_form.pk}  "Loan Application"  (multi-step, conditions, rules)')

        self.contact_form, created = Form.objects.get_or_create(
            owner=self.testuser,
            name='Contact Form',
            defaults={
                'version': 1,
                'schema': CONTACT_SCHEMA,
                'is_published': True,
            }
        )
        status = 'Created' if created else 'Already exists'
        self.stdout.write(f'  {status} → Form id={self.contact_form.pk}  "Contact Form"  (single-step)')

    def _create_submissions(self):
        self.stdout.write('Creating submissions...')

        loan_submissions = [
            {
                # salary > 100000 → rule sets status = "pre-approved"
                'full_name': 'Alice Johnson',
                'email': 'alice@example.com',
                'employment_status': 'employed',
                'salary': 120000,
                'loan_amount': 50000,
                'loan_purpose': 'home',
                'status': 'pre-approved',
            },
            {
                # salary <= 100000 → rule sets _status = "under_review"
                # loan_purpose = education → rule adds tag "education_loan"
                'full_name': 'Bob Smith',
                'email': 'bob@example.com',
                'employment_status': 'employed',
                'salary': 75000,
                'loan_amount': 200000,
                'loan_purpose': 'education',
                '_status': 'under_review',
                '_tags': ['education_loan'],
            },
            {
                # self-employed → salary hidden, business_revenue visible
                'full_name': 'Carol White',
                'email': 'carol@example.com',
                'employment_status': 'self-employed',
                'business_revenue': 80000,
                'loan_amount': 150000,
                'loan_purpose': 'business',
            },
        ]

        contact_submissions = [
            {
                # subject = support → rule adds tag "needs_support"
                'name': 'David Lee',
                'email': 'david@example.com',
                'subject': 'support',
                'message': 'I need help with my account login.',
                '_tags': ['needs_support'],
            },
            {
                'name': 'Eve Turner',
                'email': 'eve@example.com',
                'subject': 'sales',
                'message': 'I am interested in your enterprise plan.',
            },
        ]

        for data in loan_submissions:
            sub, created = Submission.objects.get_or_create(
                form=self.loan_form,
                data=data,
                defaults={'version': self.loan_form.version}
            )
            if created:
                self.stdout.write(f'  Created submission id={sub.pk}  [{self.loan_form.name}]  {data["full_name"]}')

        for data in contact_submissions:
            sub, created = Submission.objects.get_or_create(
                form=self.contact_form,
                data=data,
                defaults={'version': self.contact_form.version}
            )
            if created:
                self.stdout.write(f'  Created submission id={sub.pk}  [{self.contact_form.name}]  {data["name"]}')

    def _create_draft(self):
        self.stdout.write('Creating draft...')

        draft, created = DraftSubmission.objects.get_or_create(
            user=self.testuser,
            form=self.contact_form,
            defaults={
                'partial_data': {
                    'name': 'Test User',
                    'email': 'test@example.com',
                    'subject': 'billing',
                }
            }
        )
        status = 'Created' if created else 'Already exists'
        self.stdout.write(f'  {status} → Draft id={draft.pk}  [Contact Form]  (3 of 4 fields filled)')
