# BussGPT: Financial Transcript Analysis and Summarization

BussGPT is a system for analyzing and summarizing financial earnings call transcripts. It uses state-of-the-art AI models from Anthropic to generate insights from complex financial data.

## Features

- **Document Summaries**: Summarize individual earnings call transcripts
- **Category Summaries**: Generate comprehensive overviews across multiple quarters for a specific company
- **Complete History**: Analyze the entire history of a company's earnings calls to identify trends, challenges, and opportunities

## Setup

1. Clone this repository
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Set up MongoDB (must be running on localhost:27017)
4. Set your Anthropic API key:
   ```
   export ANTHROPIC_API_KEY="your-api-key-here"
   ```

## Usage

### Summarize Individual Transcripts

```bash
python save_summary.py --document-id <document_id> --max-words 1000
```

### Summarize a Specific Company Category

```bash
python summarize_category.py --category AAPL [--transcript-limit 100] [--dry-run]
```

The `--transcript-limit` option controls how many of the most recent transcripts to include (default: 100, which is typically all available transcripts).

### Generate All Summaries

```bash
python generate_all_summaries.py [--mode documents|categories|departments|all] [--dry-run]
```

Options:
- `--category AAPL`: Process only the specified category
- `--dry-run`: Test without making actual API calls
- `--skip-existing`: Skip categories that already have summaries
- `--yes`: Skip confirmation prompts
- `--mode`: Choose which types of summaries to generate

### Extract Summary to Text File

```bash
python extract_summary_to_file.py --category AAPL --output aapl_summary.txt
```

## Key Files

- `summarize_category.py`: Generates summaries for a specific company using their earnings call transcripts
- `extract_summary_to_file.py`: Exports a summary from the database to a text file
- `generate_all_summaries.py`: Batch processing for all categories/companies
- `improved_summary_prompts_config.json`: Configuration for summary structure and prompts

## Example Summaries

Example generated summaries are stored in the `summary_examples/` directory.

## Summary Structure

The category summaries typically include:

- Executive Summary
- Financial Performance
- Strategic Initiatives
- Market Positioning
- Technology & Innovation
- Regulatory & Compliance
- Chronological Analysis
- Segment Performance
- Geographic Performance
- Management Commentary
- Smart Money Quotes
- Operational Highlights
- Risk Assessment
- Transcript Metadata

## Requirements

- Python 3.8+
- MongoDB
- Anthropic API key (Claude 3 Opus or Sonnet)

# Earnings Transcript Database

This project imports earnings call transcripts into MongoDB for later use with LLM applications.

## Setup Instructions

1. Install MongoDB
   - Download and install MongoDB from https://www.mongodb.com/try/download/community
   - Start the MongoDB service

2. Set up Python environment
   ```bash
   # Create a virtual environment (optional but recommended)
   python -m venv venv
   
   # Activate the virtual environment
   # On macOS/Linux:
   source venv/bin/activate
   # On Windows:
   venv\Scripts\activate
   
   # Install required packages
   pip install -r requirements.txt
   ```

3. Import transcripts
   ```bash
   python import_transcripts.py
   ```

4. Update documents with metadata (date, quarter, fiscal year)
   ```bash
   python update_transcripts.py
   ```

5. Calculate token counts for LLM usage
   ```bash
   python add_token_counts.py
   ```

6. Restructure database (if needed)
   ```bash
   python restructure_db.py
   ```

## Database Structure

### Collections

The database consists of the following collections:

1. **transcripts**: Contains the actual transcript documents
   ```
   {
     "document_id": "1bb659b7-96c3-4be3-af0a-6e690a89a36e",  // Unique document ID
     "category_id": "5602d908-a5c5-43c1-b888-975dff32a2c4",  // Reference to category ID
     "category": "NVDA",                                     // Category name (ticker)
     "transcript_text": "...",                               // Full transcript text
     "date": ISODate("2020-08-19T00:00:00Z"),               // Date of earnings call
     "quarter": 2,                                          // Quarter number (1-4)
     "fiscal_year": 2021,                                   // Fiscal year
     "filename": "2020-Aug-19-NVDA.txt",                    // Original filename
     "token_count": 11557                                   // Number of tokens in the text
   }
   ```

2. **document_summaries**: Contains summaries of individual transcripts
   ```
   {
     "document_id": "ae5e9f7b-f64a-4be4-8fa2-8d6989a1d6e3",  // ID of the source document
     "category_id": "AMZN",                                  // Category identifier
     "summary_text": "...",                                  // The generated summary
     "wordcount": 1025,                                      // Word count of the summary
     "input_tokens": 7982,                                   // Tokens sent to the API
     "output_tokens": 1234,                                  // Tokens received from the API
     "last_updated": ISODate("2023-04-19T12:00:00Z")        // Timestamp
   }
   ```

3. **category_summaries**: Contains cross-quarter analyses for each company
   ```
   {
     "category_id": "AMZN",                                 // Category identifier
     "summary_text": "...",                                 // The generated summary
     "wordcount": 1548,                                     // Word count of the summary
     "transcript_count": 5,                                 // Number of transcripts analyzed
     "input_tokens": 15735,                                 // Tokens sent to the API
     "output_tokens": 2541,                                 // Tokens received from the API
     "last_updated": ISODate("2023-04-19T12:30:00Z")        // Timestamp
   }
   ```

4. **department_summaries**: Contains sector-level summaries across companies
   ```
   {
     "department_id": "TECH",                              // Department/sector identifier
     "summary": {                                          // Structured summary data
       "strategic_summary": "...",
       "cross_category_comparisons": ["...", "..."],
       "key_risks": ["...", "..."],
       "opportunities": ["...", "..."],
       "category_relationships": [{...}],
       "priority_categories": ["AAPL", "AMZN"]
     },
     "last_updated": ISODate("2023-04-19T13:00:00Z"),      // Timestamp
     "model": "claude-3-haiku-20240307",                   // Model used
     "category_ids": ["AAPL", "AMZN", "INTC", "MU"]        // Categories included
   }
   ```

### Indices

The following indices are created for efficient querying:
- Text index on `transcript_text` field for full-text search
- Index on `category` field for filtering by company
- Index on `date` field for filtering by time period
- Index on `category_id` field for joining with categories
- Index on `token_count` field for filtering by token count

## Querying the Database

### General Queries

The `query_new_structure.py` script provides a command-line interface for searching the database:

```bash
# Show database statistics (including token counts)
python query_new_structure.py --stats

# List all available categories
python query_new_structure.py --list-categories

# Search by category (most recent first)
python query_new_structure.py --category NVDA --limit 5

# Search by date range
python query_new_structure.py --start-date 2019-01-01 --end-date 2019-12-31

# Search by text content (uses MongoDB text search)
python query_new_structure.py --text "artificial intelligence" --limit 3

# Combined search (category + text)
python query_new_structure.py --category NVDA --text "deep learning" --limit 2

# Show content previews with search results
python query_new_structure.py --category NVDA --limit 1 --verbose
```

### Token-Based Queries

The `query_by_tokens.py` script allows querying based on token count, which is useful for LLM usage:

```bash
# Show token count statistics
python query_by_tokens.py --stats

# Find documents with more than 15,000 tokens
python query_by_tokens.py --min-tokens 15000

# Find documents with fewer than 8,000 tokens
python query_by_tokens.py --max-tokens 8000

# Find documents within a token range
python query_by_tokens.py --min-tokens 10000 --max-tokens 12000

# Combine token count with category filtering
python query_by_tokens.py --min-tokens 12000 --category NVDA --limit 3
```

## Hierarchical Summarization System

This project implements a three-level hierarchical summarization system for earnings call transcripts:

### Summarization Levels

1. **Document Summaries** - Individual transcript summaries
2. **Category Summaries** - Company-level summaries across multiple earnings calls
3. **Department Summaries** - Industry/sector-level summaries across multiple companies

### Architecture Flow

```
Transcripts → Document Summaries → Category Summaries → Department Summaries
    (Raw)          (Level 1)           (Level 2)           (Level 3)
```

### Unified Summarization Tool

The `generate_summaries.py` script provides a unified interface for generating all levels of summaries:

```bash
# Display current summary statistics
python generate_summaries.py --stats

# Generate document summary
python generate_summaries.py --document "ae5e9f7b-f64a-4be4-8fa2-8d6989a1d6e3"

# Generate category summary
python generate_summaries.py --category AAPL

# Generate department summary
python generate_summaries.py --department TECH --categories AAPL AMZN INTC MU

# Batch generate document summaries
python generate_summaries.py --all-documents --filter-category NVDA --limit 5

# Batch generate category summaries
python generate_summaries.py --all-categories --categories AAPL AMZN INTC MU

# Do a dry run to see what would be generated
python generate_summaries.py --all-departments --dry-run
```

For more detailed information about the hierarchical summarization system, see [HIERARCHICAL_SUMMARIZATION.md](HIERARCHICAL_SUMMARIZATION.md).

## Transcript Summarization with Claude

The project includes additional tools to summarize earnings call transcripts using Claude:

### 1. Configurable Summarization System

The project uses a modular, configurable summarization system with templates in `summary_prompts_config.json`:

```bash
# Set your API key as an environment variable
export ANTHROPIC_API_KEY="your_api_key_here"

# Use the helper script to generate summaries
./summarize.sh -c NVDA            # Summarize most recent NVDA transcript
./summarize.sh -d ae5e9f7b-f64a-4be4-8fa2-8d6989a1d6e3  # Summarize specific document
./summarize.sh -c NVDA -C         # Generate NVDA category summary
./summarize.sh -c AAPL -o apple_summary.txt  # Save to file
```

### 2. Real Summarization with Claude API

```bash
# Set your Anthropic API key in the run_summarizer.sh script
nano run_summarizer.sh

# Make the script executable
chmod +x run_summarizer.sh

# Run the summarizer
./run_summarizer.sh --category NVDA
```

You can also run the script directly:
```bash
# Set your API key as an environment variable
export ANTHROPIC_API_KEY="your_api_key_here"

# Run the summarizer
python summarize_transcript.py --category AAPL
```

### 3. Demo Summarizer (No API Key Required)

For demonstration purposes, you can use the demo summarizer which doesn't require an API key:

```bash
python summarize_demo.py --category MSFT
```

Additional options:
```bash
# Summarize by document ID
python summarize_demo.py --document-id "1bb659b7-96c3-4be3-af0a-6e690a89a36e"

# Adjust maximum words in summary
python summarize_demo.py --category GOOGL --max-words 30
```

### 4. Batch Summary Generation

To generate summaries for multiple documents or categories at once, you can use the provided batch processing scripts:

```bash
# Generate summaries for all documents
python generate_all_summaries.py --documents

# Generate summaries for all categories
python generate_all_summaries.py --categories

# Generate summaries for a specific category's documents
python generate_all_summaries.py --documents --category NVDA

# Limit the number of documents to process
python generate_all_summaries.py --documents --limit 10
```

## Token Counting for LLM Usage

The project includes functionality for calculating and storing token counts for each transcript, which is useful for:

1. **LLM Context Window Planning**: Knowing how many tokens each transcript contains helps determine if it fits within an LLM's context window.

2. **Cost Estimation**: Token counts can be used to estimate API costs when using services like Claude or GPT.

3. **Optimizing Queries**: You can target shorter or longer transcripts depending on your use case.

Token counts are calculated using the `cl100k_base` tokenizer, which is compatible with Claude models.

## Usage with LLMs

These transcripts can be used with LLMs for various analytical tasks:
- Sentiment analysis of earnings calls
- Tracking technology trends over time
- Comparing how different companies discuss similar topics
- Extracting financial guidance and performance metrics
- Analyzing executive communication styles

# BussGPT

BussGPT provides an AI-powered interface for analyzing business transcripts to extract insights and summaries. This tool processes earnings call transcripts and can generate hierarchical summaries from the document level to departments.

## Proposed Directory Structure
The codebase will be restructured to improve organization and maintainability:

```
BussGPT/
├── core/                     # Core functionality 
│   ├── db/                   # Database operations
│   ├── models/               # Data models and schemas
│   └── api/                  # API endpoints
├── tools/                    # Tool modules
│   ├── langchain_tools/      # LangChain integration
│   └── summary_tools/        # Summarization utilities
├── scripts/                  # Maintenance and utility scripts
│   ├── cleanup/              # Database and file cleanup
│   └── import/               # Data import utilities
├── summarizers/              # Summary generation modules
│   ├── document/             # Document-level summarizers
│   ├── category/             # Category-level summarizers
│   └── department/           # Department-level summarizers
├── utils/                    # Utility functions
├── config/                   # Configuration files
├── tests/                    # Test modules
├── data/                     # Data storage (non-version controlled)
│   └── transcripts/          # Transcript storage
├── logs/                     # Log files
└── web/                      # Web interface (if applicable)
```

# BussGPT Agent UI

A chat interface for interacting with the BussGPT agent.

## Features

- Real-time chat with the BussGPT agent
- View agent's thinking process
- Clean, modern interface
- Socket.IO-based communication

## Setup Instructions

### Backend Setup

1. Create and activate a virtual environment:
   ```
   python3 -m venv venv
   source venv/bin/activate
   ```

2. Install required packages:
   ```
   pip install flask flask-socketio flask-cors
   ```

3. Run the backend server:
   ```
   python server.py
   ```
   The server will run on http://localhost:5000

### Frontend Setup

1. Navigate to the Angular app directory:
   ```
   cd agent-ui/agent-ui
   ```

2. Install dependencies:
   ```
   npm install
   ```

3. Start the development server:
   ```
   npm start
   ```
   The application will be available at http://localhost:4200

## Usage

1. Open your browser and navigate to http://localhost:4200
2. Type a message in the input field and press Enter or click Send
3. The agent will respond and show its thinking process

## Development

- Backend: Flask + Socket.IO
- Frontend: Angular 19 + Socket.IO client

## License

MIT 