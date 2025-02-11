ALTER TABLE profiles
ADD COLUMN userRole TEXT CHECK (char_length(userRole) <= 50);