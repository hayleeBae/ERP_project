# Generated by Django 3.2.3 on 2023-01-31 14:31

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('don_home', '0010_alter_ablyproductinfo_price'),
    ]

    operations = [
        migrations.CreateModel(
            name='TestDB',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('test', models.CharField(max_length=50)),
            ],
        ),
    ]