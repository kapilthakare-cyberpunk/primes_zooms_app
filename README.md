# Primes & Zooms AI Assistant

This is a local web application designed for Primes & Zooms, a photo and cine gear rental service. It provides two main AI-powered modes: **Rental Consultant** and **Pricing Assistant**, to help manage inventory and assist with customer inquiries and pricing strategies.

## Features

- **CSV Inventory Loading**: Easily upload your gear inventory via a CSV file.
- **Groq API Integration**: Utilizes the Groq API for fast and efficient LLM responses.
- **DuckDuckGo Search Integration**: Provides real-time web search capabilities for product information.
- **Rental Consultant Mode**: Assists users with product information, alternative suggestions, and related item recommendations based on inventory and web data.
- **Pricing Assistant Mode**: Helps analyze current pricing structures and suggests optimal rental pricing for new or existing products.
- **Clean User Interface**: Built with Streamlit for an intuitive and professional local web experience.

## Requirements

- Python 3.7+
- `pip` (Python package installer)

## Setup and Installation

1.  **Clone the repository (or download the files):**

    ```bash
    git clone <repository_url>
    cd primes_zooms_app
    ```

    *(Note: Replace `<repository_url>` with the actual repository URL if applicable, otherwise ensure all files are in a directory named `primes_zooms_app`)*

2.  **Install dependencies:**

    Navigate to the project directory and run the following command to install all required Python packages:

    ```bash
    pip install -r requirements.txt
    ```

## Usage

1.  **Start the application:**

    From the project directory, execute the start script:

    ```bash
    ./start.sh
    ```

    This will open the Streamlit application in your default web browser.

2.  **Enter Groq API Key:**

    In the sidebar of the application, enter your Groq API Key. This is essential for the AI features to function.

3.  **Upload Inventory CSV:**

    Use the file uploader in the sidebar to select and upload your inventory CSV file. Ensure your CSV file has the following columns:
    `"Sr No", Type, "Res Type", "Res Grp", SKU, "Item ID", "Item Name", "1 Day", "2-4 Days", "5-8 Days", "9+ Days", Status, "Tax Rate", MRP, "Last Update"`

4.  **Select AI Mode and Chat:**

    Choose between "Rental Consultant" and "Pricing Assistant" modes. Then, use the chat interface to interact with the AI.

    -   **Rental Consultant**: Ask questions about specific items, their uses, or seek recommendations.
    -   **Pricing Assistant**: Provide an item name (and optionally category or current MRP) to get pricing suggestions.

## Project Structure

```
primes_zooms_app/
├── app.py              # Main Streamlit application file
├── csv_processor.py    # Handles CSV inventory loading and searching
├── ai_agents.py        # Contains AI agent logic for Rental Consultant and Pricing Assistant
├── requirements.txt    # Lists all Python dependencies
├── start.sh            # Script to install dependencies and start the application
└── README.md           # This setup and usage guide
```

## Troubleshooting

-   If the application doesn't start, ensure all dependencies are installed (`pip install -r requirements.txt`).
-   Check your Groq API key if AI responses are not working.
-   Verify your CSV file format if inventory loading fails.

---

**Primes & Zooms**
*Your trusted partner for photo and cine gear rentals in Pune.*
