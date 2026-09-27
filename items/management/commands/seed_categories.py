from django.core.management.base import BaseCommand
from items.models import Category

DEFAULT_CATEGORIES = [
    ('Electronics', 'Phones, laptops, chargers, headphones, smartwatches, etc.'),
    ('Documents & IDs', 'Passports, driver licenses, student IDs, certificates, cards.'),
    ('Wallets & Purses', 'Wallets, purses, money clips, cardholders.'),
    ('Keys & Keychains', 'House keys, car keys, lockers, key fobs.'),
    ('Bags & Backpacks', 'Backpacks, shoulder bags, suitcases, tote bags.'),
    ('Clothing & Accessories', 'Jackets, hats, gloves, scarves, sunglasses, umbrellas.'),
    ('Books & Stationery', 'Textbooks, notebooks, binders, pencil cases, calculators.'),
    ('Jewelry & Watches', 'Rings, necklaces, bracelets, wristwatches.'),
    ('Sports Equipment', 'Water bottles, gym bags, sports balls, rackets.'),
    ('Others', 'Miscellaneous items not covered by other categories.'),
]

class Command(BaseCommand):
    help = 'Seeds initial standard categories for items'

    def handle(self, *args, **options):
        created_count = 0
        for name, desc in DEFAULT_CATEGORIES:
            obj, created = Category.objects.get_or_create(
                name=name,
                defaults={'description': desc}
            )
            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f'Created category: {name}'))
            else:
                self.stdout.write(f'Category already exists: {name}')

        self.stdout.write(self.style.SUCCESS(f'Done! Added {created_count} categories.'))
