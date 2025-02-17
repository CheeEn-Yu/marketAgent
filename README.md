# AI Market Agent – Real-time Financial Data Analysis
#1st place, TSMC IT CareerHack 2025

This project introduces an AI Market Agent, a generative AI-powered assistant that enables users to interact with financial data through natural language. The agent automatically analyzes financial reports, retrieves key insights from CSV data and earnings call transcripts, and generates visualized financial summaries—all without requiring IT team intervention.

# Team members
[Chee-En Yu](https://github.com/CheeEn-Yu), [Chia-Hua Yang](https://github.com/joker-abc), [Wei-Chin Wang](https://github.com/wwchin), [Teng-Yun Hsiao](https://scholar.google.com.tw/citations?user=rXbijt8AAAAJ&hl=zh-TW)

# Key features
- Automated Financial Data Analysis – Generates real-time financial insights and reports.
- Data Retrieval & Visualization – Extracts key indicators from CSV files and earnings transcripts, presenting insights in an intuitive format.

# Introduction
The AI Market Agent leverages [plan-and-solve prompting](https://langchain-ai.github.io/langgraph/tutorials/plan-and-execute/plan-and-execute/) to break down complex financial queries, an agent graph to manage multi-step reasoning, and a [CSV agent in LangChain](https://python.langchain.com/v0.2/api_reference/cohere/csv_agent/langchain_cohere.csv_agent.agent.create_csv_agent.html) for structured data extraction. It also employs [function calling with vertex AI](https://cloud.google.com/vertex-ai/generative-ai/docs/multimodal/function-calling) to dynamically select the best analytical tools and self-refinement techniques to minimize hallucinations, ensuring more accurate responses. All implementation can be found in the [python_backend/](./python_backend/) folder. We have also open-sourced the final presentation slides, as well as the CSV data and earnings call transcripts used in the competition, which can be found in the [docs/](./docs/) folder.

## UI template
We adopted [Chatbot UI](https://www.chatbotui.com/) as the user interface. Below is a simple guide on how to run this UI locally. For more details, please refer to the original repository.

### Updating

In your terminal at the root of your local Chatbot UI repository, run:

```bash
npm run update
```

If you run a hosted instance you'll also need to run:

```bash
npm run db-push
```

to apply the latest migrations to your live database.

### Local Quickstart

Follow these steps to get your own Chatbot UI instance running locally.

You can watch the full video tutorial [here](https://www.youtube.com/watch?v=9Qq3-7-HNgw).

#### 1. Clone the Repo

```bash
git clone https://github.com/mckaywrigley/chatbot-ui.git
```

#### 2. Install Dependencies

Open a terminal in the root directory of your local Chatbot UI repository and run:

```bash
npm install
```

#### 3. Install Supabase & Run Locally

##### Why Supabase?

Previously, we used local browser storage to store data. However, this was not a good solution for a few reasons:

- Security issues
- Limited storage
- Limits multi-modal use cases

We now use Supabase because it's easy to use, it's open-source, it's Postgres, and it has a free tier for hosted instances.

We will support other providers in the future to give you more options.

##### 1. Install Docker

You will need to install Docker to run Supabase locally. You can download it [here](https://docs.docker.com/get-docker) for free.

##### 2. Install Supabase CLI

**MacOS/Linux**

```bash
brew install supabase/tap/supabase
```

**Windows**

```bash
scoop bucket add supabase https://github.com/supabase/scoop-bucket.git
scoop install supabase
```

##### 3. Start Supabase

In your terminal at the root of your local Chatbot UI repository, run:

```bash
supabase start
```

#### 4. Fill in Secrets

##### 1. Environment Variables

In your terminal at the root of your local Chatbot UI repository, run:

```bash
cp .env.local.example .env.local
```

Get the required values by running:

```bash
supabase status
```

Note: Use `API URL` from `supabase status` for `NEXT_PUBLIC_SUPABASE_URL`

Now go to your `.env.local` file and fill in the values.

If the environment variable is set, it will disable the input in the user settings.

##### 2. SQL Setup

In the 1st migration file `supabase/migrations/20240108234540_setup.sql` you will need to replace 2 values with the values you got above:

- `project_url` (line 53): `http://supabase_kong_chatbotui:8000` (default) can remain unchanged if you don't change your `project_id` in the `config.toml` file
- `service_role_key` (line 54): You got this value from running `supabase status`

This prevents issues with storage files not being deleted properly.

#### 5. Install Ollama (optional for local models)

Follow the instructions [here](https://github.com/jmorganca/ollama#macos).

#### 6. Run app locally

In your terminal at the root of your local Chatbot UI repository, run:

```bash
npm run chat
```

Your local instance of Chatbot UI should now be running at [http://localhost:3000](http://localhost:3000). Be sure to use a compatible node version (i.e. v18).

You can view your backend GUI at [http://localhost:54323/project/default/editor](http://localhost:54323/project/default/editor).

### Hosted Quickstart

Follow these steps to get your own Chatbot UI instance running in the cloud.

Video tutorial coming soon.

#### 1. Follow Local Quickstart

Repeat steps 1-4 in "Local Quickstart" above.

You will want separate repositories for your local and hosted instances.

Create a new repository for your hosted instance of Chatbot UI on GitHub and push your code to it.

#### 2. Setup Backend with Supabase

##### 1. Create a new project

Go to [Supabase](https://supabase.com/) and create a new project.

##### 2. Get Project Values

Once you are in the project dashboard, click on the "Project Settings" icon tab on the far bottom left.

Here you will get the values for the following environment variables:

- `Project Ref`: Found in "General settings" as "Reference ID"

- `Project ID`: Found in the URL of your project dashboard (Ex: https://supabase.com/dashboard/project/<YOUR_PROJECT_ID>/settings/general)

While still in "Settings" click on the "API" text tab on the left.

Here you will get the values for the following environment variables:

- `Project URL`: Found in "API Settings" as "Project URL"

- `Anon key`: Found in "Project API keys" as "anon public"

- `Service role key`: Found in "Project API keys" as "service_role" (Reminder: Treat this like a password!)

##### 3. Configure Auth

Next, click on the "Authentication" icon tab on the far left.

In the text tabs, click on "Providers" and make sure "Email" is enabled.

We recommend turning off "Confirm email" for your own personal instance.

##### 4. Connect to Hosted DB

Open up your repository for your hosted instance of Chatbot UI.

In the 1st migration file `supabase/migrations/20240108234540_setup.sql` you will need to replace 2 values with the values you got above:

- `project_url` (line 53): Use the `Project URL` value from above
- `service_role_key` (line 54): Use the `Service role key` value from above

Now, open a terminal in the root directory of your local Chatbot UI repository. We will execute a few commands here.

Login to Supabase by running:

```bash
supabase login
```

Next, link your project by running the following command with the "Project ID" you got above:

```bash
supabase link --project-ref <project-id>
```

Your project should now be linked.

Finally, push your database to Supabase by running:

```bash
supabase db push
```

Your hosted database should now be set up!

#### 3. Setup Frontend with Vercel

Go to [Vercel](https://vercel.com/) and create a new project.

In the setup page, import your GitHub repository for your hosted instance of Chatbot UI. Within the project Settings, in the "Build & Development Settings" section, switch Framework Preset to "Next.js".

In environment variables, add the following from the values you got above:

- `NEXT_PUBLIC_SUPABASE_URL`
- `NEXT_PUBLIC_SUPABASE_ANON_KEY`
- `SUPABASE_SERVICE_ROLE_KEY`
- `NEXT_PUBLIC_OLLAMA_URL` (only needed when using local Ollama models; default: `http://localhost:11434`)

You can also add API keys as environment variables.

- `OPENAI_API_KEY`
- `AZURE_OPENAI_API_KEY`
- `AZURE_OPENAI_ENDPOINT`
- `AZURE_GPT_45_VISION_NAME`

For the full list of environment variables, refer to the '.env.local.example' file. If the environment variables are set for API keys, it will disable the input in the user settings.

Click "Deploy" and wait for your frontend to deploy.

Once deployed, you should be able to use your hosted instance of Chatbot UI via the URL Vercel gives you.

# Acknowledgement

The success of this competition would not have been possible without the dedication and sleepless nights shared with my teammates. Additionally, I want to express my deepest gratitude to a silent supporter: [Sun Paris](https://github.com/SunParis)

Thank you for working with me on backend-frontend communication, and for being the most insightful computer science students I know, especially in understanding programming languages. Even though you weren’t part of the competition, you stayed up until 4 AM with me, helping to build the very first version of our system. Wishing you all the best in your research and studies—your hard work and knowledge will surely take you far! 🚀
