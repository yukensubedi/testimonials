# Generated by Django 5.1.2 on 2024-10-23 14:02

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0003_question'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='spaces',
            options={'ordering': ['-created_at']},
        ),
        migrations.RenameField(
            model_name='spaces',
            old_name='space_logo',
            new_name='spaces_logo',
        ),
        migrations.RenameField(
            model_name='spaces',
            old_name='space_name',
            new_name='spaces_name',
        ),
        migrations.CreateModel(
            name='Testimonials',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('testimonial_text', models.TextField()),
                ('sender_name', models.CharField(max_length=200)),
                ('sender_email', models.EmailField(max_length=254, verbose_name='email address')),
                ('star_rating', models.PositiveSmallIntegerField(blank=True, choices=[(1, '1 Stars'), (2, '2 Stars'), (3, '3 Stars'), (4, '4 Stars'), (5, '5 Stars')], null=True)),
                ('spaces', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='testimonials', to='app.spaces')),
            ],
            options={
                'abstract': False,
            },
        ),
    ]
