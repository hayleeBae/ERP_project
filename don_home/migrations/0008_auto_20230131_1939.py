# Generated by Django 3.2.3 on 2023-01-31 10:39

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('don_home', '0007_alter_ablysalesinfo_ordernumber'),
    ]

    operations = [
        migrations.AlterField(
            model_name='ablyproductinfo',
            name='discountPrice',
            field=models.CharField(max_length=100),
        ),
        migrations.AlterField(
            model_name='ablyproductinfo',
            name='extraShippingCost',
            field=models.CharField(max_length=100),
        ),
        migrations.AlterField(
            model_name='ablyproductinfo',
            name='parcel',
            field=models.CharField(max_length=100),
        ),
        migrations.AlterField(
            model_name='ablyproductinfo',
            name='price',
            field=models.CharField(max_length=50),
        ),
        migrations.AlterField(
            model_name='ablyproductinfo',
            name='productNumber',
            field=models.CharField(max_length=100),
        ),
        migrations.AlterField(
            model_name='ablyproductinfo',
            name='registrationDate',
            field=models.CharField(max_length=100),
        ),
        migrations.AlterField(
            model_name='ablyproductinfo',
            name='returnShippingCost',
            field=models.CharField(max_length=100),
        ),
        migrations.AlterField(
            model_name='ablyproductinfo',
            name='statusDisplay',
            field=models.CharField(max_length=100),
        ),
        migrations.AlterField(
            model_name='ablyproductinfo',
            name='stock',
            field=models.CharField(max_length=100),
        ),
        migrations.AlterField(
            model_name='ablyproductinfo',
            name='totalReview',
            field=models.CharField(max_length=100),
        ),
    ]