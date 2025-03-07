# MongoDB Atlas Setup for PythonAnywhere

When deploying your Telegram Attendance Bot to PythonAnywhere, you need to make sure your MongoDB Atlas instance is properly configured to accept connections from PythonAnywhere's servers.

## Whitelist PythonAnywhere IP Addresses

1. Log in to your [MongoDB Atlas account](https://cloud.mongodb.com/)
2. Select your cluster
3. Click on "Network Access" in the left sidebar
4. Click "Add IP Address"
5. Add the following PythonAnywhere IP addresses:

   - 104.18.6.171
   - 35.173.69.207
   - 52.22.13.242
   - 34.238.119.208
     (Note: These may change, check PythonAnywhere's documentation for current IPs)

6. Alternatively, if this is just for development/personal use, you can allow access from anywhere by adding `0.0.0.0/0`
   (Not recommended for production applications for security reasons)

## Test Your MongoDB Connection

To test your MongoDB connection from PythonAnywhere:

1. Open a PythonAnywhere console
2. Activate your virtual environment:
   ```bash
   source ~/telegramattendancebot/venv/bin/activate
   ```
3. Run a simple connection test:
   ```python
   python -c "from pymongo import MongoClient; client = MongoClient('your_mongodb_uri'); print(client.server_info())"
   ```
4. If successful, you should see information about your MongoDB server

## Troubleshooting MongoDB Connection Issues

If you can't connect to MongoDB from PythonAnywhere:

1. Double-check the IP addresses in your MongoDB Atlas whitelist
2. Ensure your MongoDB URI is correctly specified in your .env file
3. Make sure your MongoDB Atlas cluster is running (not paused)
4. Check if your MongoDB Atlas account has active restrictions (free tier limits, etc.)
5. Verify network connectivity by trying to connect to another internet service

## Security Best Practices

1. Create a dedicated MongoDB database user with minimum required permissions
2. Use a strong password for your MongoDB Atlas account and database users
3. Regularly update your whitelist to remove unnecessary IPs
4. Enable MongoDB Atlas auditing to monitor access to your database
5. Regularly backup your database
