-- ENRICH REFERENCE DATA — categories, shelf life, menu prices

-- 1. Add category and shelf_life_days to ingredients
ALTER TABLE ingredients ADD COLUMN IF NOT EXISTS category TEXT DEFAULT 'other';
ALTER TABLE ingredients ADD COLUMN IF NOT EXISTS shelf_life_days SMALLINT;

-- 2. Populate categories and shelf life for all 46 ingredients
-- Proteins
UPDATE ingredients SET category = 'protein', shelf_life_days = 3
  WHERE ingredient_name IN ('Beef Patty', 'Chicken Breast', 'White Fish', 'Sirloin Steak');

-- Dairy
UPDATE ingredients SET category = 'dairy', shelf_life_days = 14
  WHERE ingredient_name IN ('Cheddar', 'Mozzarella', 'Parmesan', 'Cream', 'Milk', 'Butter');

UPDATE ingredients SET category = 'dairy', shelf_life_days = 7
  WHERE ingredient_name = 'Eggs';

-- Produce
UPDATE ingredients SET category = 'produce', shelf_life_days = 5
  WHERE ingredient_name IN ('Lettuce', 'Tomato', 'Onion', 'Romaine', 'Basil', 'Cabbage', 'Lemon', 'Garlic');

UPDATE ingredients SET category = 'produce', shelf_life_days = 10
  WHERE ingredient_name = 'Potatoes';

UPDATE ingredients SET category = 'produce', shelf_life_days = 7
  WHERE ingredient_name IN ('Tomatoes (Soup)');

-- Bakery / bread (short shelf life)
UPDATE ingredients SET category = 'bakery', shelf_life_days = 3
  WHERE ingredient_name IN ('Brioche Bun', 'Pizza Dough', 'Tortillas');

-- Condiments / sauces
UPDATE ingredients SET category = 'condiment', shelf_life_days = 30
  WHERE ingredient_name IN ('House Sauce', 'Caesar Dressing', 'Tomato Sauce',
                            'Pico de Gallo', 'Lime Crema', 'Marinara', 'Chocolate Ganache',
                            'Herb Butter', 'Vanilla Syrup');

UPDATE ingredients SET category = 'condiment', shelf_life_days = 14
  WHERE ingredient_name = 'Pickles';

-- Dry goods / non-perishable
UPDATE ingredients SET category = 'dry_goods', shelf_life_days = 365
  WHERE ingredient_name IN ('Salt', 'Black Pepper', 'Cocoa', 'Flour', 'Sugar',
                            'Croutons', 'Pasta');

-- Oils / liquids (long shelf life)
UPDATE ingredients SET category = 'oil', shelf_life_days = 180
  WHERE ingredient_name IN ('Olive Oil', 'Frying Oil');

-- Beverages
UPDATE ingredients SET category = 'beverage', shelf_life_days = 30
  WHERE ingredient_name IN ('Espresso', 'Craft Soda Base');

UPDATE ingredients SET category = 'beverage', shelf_life_days = 7
  WHERE ingredient_name = 'Ice';

-- 3. Set menu item prices (realistic bistro pricing)
UPDATE menu_items SET price = 14.50  WHERE item_name = 'Caesar Salad';
UPDATE menu_items SET price = 15.95  WHERE item_name = 'Chicken Sandwich';
UPDATE menu_items SET price = 10.50  WHERE item_name = 'Chocolate Cake';
UPDATE menu_items SET price = 16.95  WHERE item_name = 'Classic Burger';
UPDATE menu_items SET price = 4.50   WHERE item_name = 'Craft Soda';
UPDATE menu_items SET price = 17.50  WHERE item_name = 'Fish Tacos (3)';
UPDATE menu_items SET price = 7.95   WHERE item_name = 'French Fries';
UPDATE menu_items SET price = 6.50   WHERE item_name = 'Iced Latte';
UPDATE menu_items SET price = 9.95   WHERE item_name = 'Kids Pasta';
UPDATE menu_items SET price = 18.50  WHERE item_name = 'Margherita Pizza';
UPDATE menu_items SET price = 28.95  WHERE item_name = 'Steak Frites';
UPDATE menu_items SET price = 9.50   WHERE item_name = 'Tomato Soup';

-- 4. Give the restaurant a proper name
UPDATE restaurants SET restaurant_name = 'The Corner Bistro' WHERE restaurant_id = 1;
