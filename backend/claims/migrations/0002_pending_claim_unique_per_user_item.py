from django.db import migrations, models
from django.db.models import Count, Q


def reject_existing_pending_duplicates(apps, schema_editor):
    Claim = apps.get_model('claims', 'Claim')
    duplicates = (
        Claim.objects.using(schema_editor.connection.alias)
        .filter(status='PENDING')
        .values('item_id', 'claimant_id')
        .annotate(total=Count('id'))
        .filter(total__gt=1)
    )
    duplicate_count = duplicates.count()
    if duplicate_count:
        raise RuntimeError(
            f'Cannot add pending-claim uniqueness: found {duplicate_count} '
            'item/claimant pairs with multiple pending claims. Review and resolve '
            'the duplicate records while preserving claim history, then rerun migrations.'
        )


class Migration(migrations.Migration):

    dependencies = [
        ('claims', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(reject_existing_pending_duplicates, migrations.RunPython.noop),
        migrations.AddConstraint(
            model_name='claim',
            constraint=models.UniqueConstraint(
                fields=('item', 'claimant'),
                condition=Q(status='PENDING'),
                name='uniq_pending_claim_item_user',
            ),
        ),
    ]
