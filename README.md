# Personal AI RAG System

A Retrieval-Augmented Generation (RAG) system that answers questions about personal information using structured text documents. This system processes your personal data files, creates semantic embeddings, and uses AI to provide accurate, contextual answers to questions about your background, projects, skills, and experience.

## 🚀 Features

- **Document Processing**: Automatically loads and processes text files from your data directory
- **Intelligent Chunking**: Splits documents into semantically coherent chunks while preserving sentence boundaries
- **Semantic Search**: Uses vector embeddings to find the most relevant information for your queries
- **AI-Powered Responses**: Leverages OpenAI's GPT models to generate natural, contextual answers
- **Source Attribution**: Shows which documents were used to generate each answer
- **Interactive CLI**: Easy-to-use command-line interface for asking questions
- **Persistent Storage**: Saves processed embeddings to disk for fast startup
- **Configurable**: Extensive configuration options for customization

## 📋 Table of Contents

- [Quick Start](#quick-start)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Data Organization](#data-organization)
- [CLI Commands](#cli-commands)
- [Development](#development)
- [Troubleshooting](#troubleshooting)
- [Architecture](#architecture)

## ⚡ Quick Start

1. **Install dependencies**:
   ```bash
   uv sync
   ```

2. **Set up your OpenAI API key**:
   ```bash
   cp .env.example .env
   # Edit .env and add your OPENAI_API_KEY
   ```

3. **Add your data files** to the `data/` directory (see [Data Organization](#data-organization))

4. **Run the system**:
   ```bash
   python main.py
   ```

5. **Start asking questions**:
   ```
   > What projects have I worked on?
   > Tell me about my Python experience
   > What are my key skills?
   ```

## 🛠 Installation

### Prerequisites

- **Python 3.12+** (required)
- **OpenAI API key** (required for AI responses)
- **uv** package manager (recommended) or pip

### Step-by-Step Installation

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd personal-ai
   ```

2. **Install dependencies**:
   
   Using uv (recommended):
   ```bash
   uv sync
   uv sync --extra dev  # For development dependencies
   ```
   
   Using pip:
   ```bash
   pip install -e .
   pip install -e ".[dev]"  # For development dependencies
   ```

3. **Set up environment variables**:
   ```bash
   cp .env.example .env
   ```
   
   Edit `.env` and add your OpenAI API key:
   ```env
   OPENAI_API_KEY=your_actual_api_key_here
   ```

4. **Verify installation**:
   ```bash
   python -c "import personal_ai; print('Installation successful!')"
   ```

## ⚙️ Configuration

The system is highly configurable through environment variables or a `.env` file. All configuration options are documented in `.env.example`.

### Required Configuration

| Variable | Description | Example |
|----------|-------------|---------|
| `OPENAI_API_KEY` | Your OpenAI API key | `sk-...` |

### Optional Configuration (with defaults)

| Variable | Default | Description |
|----------|---------|-------------|
| `CHUNK_SIZE` | `500` | Maximum characters per chunk |
| `CHUNK_OVERLAP` | `50` | Overlap between consecutive chunks |
| `EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | Sentence-transformers model |
| `LLM_MODEL` | `gpt-3.5-turbo` | OpenAI model for responses |
| `N_RETRIEVAL_RESULTS` | `5` | Number of chunks to retrieve per query |
| `DATA_DIRECTORY` | `./data` | Path to your data files |
| `PERSIST_DIRECTORY` | `./chroma_db` | Vector database storage path |
| `MAX_CONTEXT_TOKENS` | `3000` | Maximum context size for LLM |
| `MAX_RESPONSE_TOKENS` | `500` | Maximum response length |
| `MAX_RETRIES` | `3` | API retry attempts |

### Configuration Examples

**Basic configuration** (`.env`):
```env
OPENAI_API_KEY=sk-your-key-here
```

**Advanced configuration** (`.env`):
```env
OPENAI_API_KEY=sk-your-key-here
CHUNK_SIZE=750
LLM_MODEL=gpt-4
N_RETRIEVAL_RESULTS=8
DATA_DIRECTORY=/path/to/my/documents
```

## 🎯 Usage

### Running the Application

```bash
python main.py
```

The system will:
1. Load your configuration
2. Check for existing vector database
3. If none exists, process all files in your data directory
4. Start the interactive CLI

### First Run

On first run, the system will:
- Load all text files from your `data/` directory
- Split them into chunks
- Generate embeddings (this may take a few minutes)
- Store everything in a local vector database
- Start the CLI interface

Subsequent runs will be much faster as the processed data is cached.

### Example Session

```
Personal AI RAG System
Type 'help' for commands, 'exit' to quit.

> What programming languages do I know?
Based on your experience, you are proficient in several programming languages including:

- **Python**: Extensive experience with web development, data analysis, and automation
- **JavaScript**: Frontend and backend development with React and Node.js
- **Go**: Backend services and API development
- **SQL**: Database design and optimization

Sources: experience.txt, projects/go_auth.txt

> Tell me about my education
You have a Bachelor's degree in Computer Science from [University Name], graduating in [Year]. 
During your studies, you focused on software engineering, algorithms, and data structures.

Sources: static/education.txt

> sources
Last query sources:
1. static/education.txt (similarity: 0.89)
   "Bachelor's degree in Computer Science from University of Technology..."

> help
Available commands:
- ask <question>: Ask a question about your data
- sources: Show sources from the last response
- rebuild: Rebuild the knowledge base from data files
- help: Show this help message
- exit/quit: Exit the application

> exit
Goodbye!
```

## 📁 Data Organization

The system expects your personal data to be organized in text files within the `data/` directory. The directory structure helps categorize your information:

### Recommended Structure

```
data/
├── static/              # Static personal information
│   ├── personal.txt     # Personal details, contact info
│   ├── education.txt    # Educational background
│   ├── experience.txt   # Work experience
│   └── resume.txt       # Resume summary
├── projects/            # Project descriptions
│   ├── project1.txt     # Individual project files
│   ├── project2.txt
│   └── ...
├── skills/              # Skills and competencies
│   └── skills.txt       # Technical and soft skills
└── achievements/        # Awards, certifications
    ├── certifications.txt
    └── awards.txt
```

### File Format Guidelines

- **Use plain text files** (`.txt` extension)
- **Write in natural language** - the system works best with conversational text
- **Include context** - add dates, company names, technologies used
- **Be specific** - detailed descriptions help with accurate retrieval

### Example File Content

**`data/static/experience.txt`**:
```
Senior Software Engineer at TechCorp (2020-2023)
- Led a team of 5 developers building microservices in Go and Python
- Designed and implemented RESTful APIs serving 1M+ requests daily
- Reduced system latency by 40% through database optimization
- Mentored junior developers and conducted code reviews

Software Developer at StartupXYZ (2018-2020)
- Built full-stack web applications using React and Node.js
- Implemented CI/CD pipelines using Docker and Jenkins
- Collaborated with product team to define technical requirements
```

**`data/projects/ecommerce-platform.txt`**:
```
E-commerce Platform (2022)

Built a scalable e-commerce platform using microservices architecture.

Technologies: Go, PostgreSQL, Redis, Docker, Kubernetes
Features: User authentication, product catalog, shopping cart, payment processing
Challenges: Handling high traffic during sales events, ensuring data consistency
Results: Successfully handled 10,000+ concurrent users during Black Friday

Key learnings: Microservices design patterns, database sharding, caching strategies
```

## 💻 CLI Commands

The interactive CLI supports several commands:

| Command | Description | Example |
|---------|-------------|---------|
| `ask <question>` | Ask a question about your data | `ask What Python frameworks do I know?` |
| `<question>` | Direct question (no "ask" needed) | `What are my recent projects?` |
| `sources` | Show sources from last response | `sources` |
| `rebuild` | Rebuild knowledge base from files | `rebuild` |
| `help` | Show available commands | `help` |
| `exit` / `quit` | Exit the application | `exit` |

### Query Tips

**Good queries**:
- "What programming languages do I know?"
- "Tell me about my experience with machine learning"
- "What projects involved React?"
- "Describe my leadership experience"

**Less effective queries**:
- "Hi" (too vague)
- "What's the weather?" (not about your data)
- Very long, complex questions with multiple parts

## 🔧 Development

### Project Structure

```
personal-ai/
├── personal_ai/           # Main package
│   ├── __init__.py
│   ├── config.py          # Configuration management
│   ├── models.py          # Data models (Document, Chunk, etc.)
│   ├── document_loader.py # File loading and processing
│   ├── text_chunker.py    # Text splitting logic
│   ├── embedding_generator.py  # Vector embedding generation
│   ├── vector_store.py    # ChromaDB vector database
│   ├── llm_client.py      # OpenAI API client
│   ├── query_engine.py    # Query processing pipeline
│   └── cli.py             # Command-line interface
├── tests/                 # Test suite
│   ├── __init__.py
│   ├── conftest.py        # Pytest fixtures
│   ├── test_config.py     # Configuration tests
│   ├── test_text_chunker.py
│   ├── test_query_engine.py
│   ├── test_llm_client.py
│   └── test_cli.py
├── data/                  # Your personal data files
├── main.py               # Application entry point
├── pyproject.toml        # Dependencies and metadata
└── README.md
```

### Running Tests

```bash
# Run all tests
uv run pytest

# Run with coverage report
uv run pytest --cov=personal_ai --cov-report=term-missing

# Run specific test file
uv run pytest tests/test_config.py -v

# Run tests with hypothesis property testing
uv run pytest tests/ -v --hypothesis-show-statistics
```

### Code Quality

```bash
# Type checking (if mypy is installed)
mypy personal_ai/

# Code formatting (if black is installed)
black personal_ai/ tests/
```

## 🐛 Troubleshooting

### Common Issues

**"No documents found in data directory"**
- Ensure the `data/` directory exists and contains `.txt` files
- Check the `DATA_DIRECTORY` configuration
- Verify file permissions

**"OpenAI API key not found"**
- Check that `OPENAI_API_KEY` is set in your `.env` file
- Ensure the API key is valid and has sufficient credits
- Verify there are no extra spaces or quotes around the key

**"ChromaDB connection error"**
- Check disk space in the `PERSIST_DIRECTORY`
- Ensure write permissions for the directory
- Try deleting the `chroma_db/` directory to rebuild

**"Embedding generation failed"**
- Check internet connection (sentence-transformers downloads models)
- Verify sufficient disk space for model files
- Try a different embedding model in configuration

**Slow performance**
- Reduce `CHUNK_SIZE` for faster processing
- Decrease `N_RETRIEVAL_RESULTS` for faster queries
- Use a smaller embedding model like `all-MiniLM-L6-v2`

### Debug Mode

Enable debug logging by setting the log level:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Getting Help

1. **Check the logs** - the application provides detailed logging
2. **Review configuration** - ensure all required settings are correct
3. **Test with minimal data** - try with just one small text file
4. **Check API quotas** - verify OpenAI API usage and limits

## 🏗 Architecture

### System Overview

The Personal AI RAG System follows a pipeline architecture:

```
Documents → Chunking → Embeddings → Vector Store → Query → LLM → Response
```

### Key Components

1. **Document Loader**: Recursively loads text files and extracts metadata
2. **Text Chunker**: Splits documents into overlapping chunks with sentence boundaries
3. **Embedding Generator**: Creates vector representations using sentence-transformers
4. **Vector Store**: Manages ChromaDB for similarity search
5. **Query Engine**: Orchestrates retrieval and response generation
6. **LLM Client**: Interfaces with OpenAI API with retry logic
7. **CLI**: Provides interactive user interface

### Data Flow

1. **Initialization**: Load documents → chunk → embed → store in vector DB
2. **Query Processing**: User question → embed query → retrieve similar chunks → construct prompt → LLM generates response
3. **Response**: Display answer with source attribution

### Design Principles

- **Modularity**: Each component has a single responsibility
- **Configurability**: Extensive configuration options
- **Error Handling**: Graceful failure with informative messages
- **Testing**: Comprehensive unit and property-based tests
- **Performance**: Efficient batch processing and caching

## 📄 License

[Add your license here]

---

**Need help?** Check the troubleshooting section above or review the design documents in `.kiro/specs/personal-ai-rag/`.
