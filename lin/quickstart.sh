#!/bin/bash

# Linkd Flutter Frontend - Quick Start Commands
# Copy and paste these commands to get started quickly

echo "🚀 Linkd Flutter Frontend - Quick Start"
echo "========================================"
echo ""

# Navigate to project
cd linkd_app || exit

# Step 1: Fetch dependencies
echo "📦 Fetching latest dependencies..."
flutter pub get

# Step 2: Configure Firebase
echo ""
echo "🔥 Configuring Firebase..."
echo "   After running flutterfire configure, select your Firebase project"
flutterfire configure

# Step 3: Run the app
echo ""
echo "▶️  Starting the app..."
flutter run

echo ""
echo "✅ Done! Your Linkd app is running!"
echo ""
echo "📝 Next steps:"
echo "1. Update .env with your Firebase credentials"
echo "2. Implement authentication screens"
echo "3. Create entity search functionality"
echo "4. Build connection management screens"
echo ""
echo "📚 Refer to SETUP_CHECKLIST.md for detailed implementation guide"
