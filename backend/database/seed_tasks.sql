-- ============================================================================
-- SEED STUDY TASKS - 1 Tutorial + 5 Real Tasks (6 Total)
-- ============================================================================
-- This script defines the 6-task structure for the experiment:
-- - Task 0: Tutorial Task (NOT analyzed - for familiarization)
-- - Tasks 1-5: Real Tasks (Analyzed - varying difficulty levels)
--
-- IMPORTANT: Tasks are auto-assigned when participants register through the app.
-- This script defines the function used during registration.
--
-- Date: 2026-02-11
-- Updated to match professor's recommendations
-- ============================================================================

-- ============================================================================
-- HELPER FUNCTION: Assign 6 Experiment Tasks (1 Tutorial + 5 Real)
-- ============================================================================
CREATE OR REPLACE FUNCTION assign_6_experiment_tasks(
    p_experiment_id VARCHAR(36),
    p_participant_id VARCHAR(36)
) RETURNS INTEGER AS $$
BEGIN
    -- ==========================================================================
    -- TASK 0: TUTORIAL TASK (NOT ANALYZED)
    -- ==========================================================================
    -- Purpose: Familiarize participants with the system interface
    -- Difficulty: Tutorial (Very Easy)
    -- Domain: Production
    -- Analysis: EXCLUDED from performance metrics

    INSERT INTO public.experiment_tasks (
        id, experiment_id, participant_id, task_id, task_number,
        task_description, task_type, domain, complexity_level,
        is_tutorial, tutorial_steps, tutorial_tips
    ) VALUES (
        gen_random_uuid()::text, p_experiment_id, p_participant_id,
        'TASK_00_TUTORIAL', 0,

        -- Task Description
        '**Role:** Inventory Manager at AdventureWorks

**Scenario:** You are the Inventory Manager at AdventureWorks. The supply chain team has flagged potential stockout risks, and you need to quickly assess the current inventory situation. Your manager wants to know how many products are running low and which category needs the most urgent attention for reordering.

**Question to Answer:**
"How many products are currently at low stock levels (below 50 units), and which product category has the most low-stock items?"',

        'data_retrieval', 'Production', 'tutorial',
        TRUE, -- is_tutorial

        -- Tutorial Steps (shown to all participants)
        '### How to Complete This Tutorial Task

This is a **practice task** to help you get familiar with the system. Take your time and explore!

---

#### For Experimental Group (Dashboard + AI Chat):

**Step 1: Explore the Dashboards**
1. Click on "Dashboards" in the navigation menu
2. Open the "Production & Inventory" dashboard
3. Look for the "Low Stock Items" table
4. Note the total count of low-stock products (shown at the top or bottom of the table)

**Step 2: Use the AI Chat Assistant (Optional)**
1. Click on "Chat" in the navigation menu
2. Try asking: "How many products have low stock?"
3. Try asking: "Which category has the most low-stock items?"
4. The AI will help you find the answer

**Step 3: Submit Your Answer**
1. Return to this task page
2. Enter your answer in the text box below
3. Click "Submit Answer"

---

#### For Control Group (Dashboard Only):

**Step 1: Explore the Dashboards**
1. Click on "Dashboards" in the navigation menu
2. Open the "Production & Inventory" dashboard
3. Look for the "Low Stock Items" table
4. Count the products with stock below 50 units (or check if there''s a total count displayed)

**Step 2: Identify the Category**
1. In the same table, look at the "Category" column
2. Count which category appears most frequently in the low-stock list
3. You can also try using any filters available in the dashboard

**Step 3: Navigate and Explore**
1. You can switch between different dashboard tabs
2. Try hovering over charts to see detailed information
3. Take your time to get comfortable with the interface

**Step 4: Submit Your Answer**
1. Return to this task page
2. Enter your answer in the text box below
3. Click "Submit Answer"

---

### Expected Answer Format

Your answer should include:
- The **number** of products with low stock (below 50 units)
- The **product category** with the most low-stock items

**Example Answer:**
"There are X products with low stock levels (below 50 units). The category with the most low-stock items is [Category Name] with Y products."

Or simply:
"X products; [Category Name] category"',

        -- Tutorial Tips
        '### Tips for Success

✅ **Take Your Time:** This is a tutorial - there''s no time pressure
✅ **Explore Freely:** Try different features to get comfortable with the interface
✅ **Ask Questions:** If using the AI chat, try different ways of asking the same question
✅ **Don''t Worry About Perfection:** This task is for learning, not evaluation
✅ **Familiarize Yourself:** Get comfortable navigating between pages and dashboards

**Remember:** This tutorial task is NOT analyzed. It''s just to help you learn the system!'
    );

    -- ==========================================================================
    -- TASK 1: SALES TERRITORY PERFORMANCE (VERY EASY)
    -- ==========================================================================
    -- Difficulty: Very Easy - Control group should solve with minimal effort
    -- Domain: Sales
    -- Expected Time: 3-5 minutes

    INSERT INTO public.experiment_tasks (
        id, experiment_id, participant_id, task_id, task_number,
        task_description, task_type, domain, complexity_level,
        is_tutorial
    ) VALUES (
        gen_random_uuid()::text, p_experiment_id, p_participant_id,
        'TASK_01', 1,
        '**Role:** Sales Analyst at AdventureWorks

**Scenario:** Your manager wants a quick overview of regional sales performance for 2024. They need to know the top-performing territories and their approximate revenue figures to plan resource allocation for the next quarter.

**Tip:** Go to the **Sales & Revenue** dashboard, use the **Time Range** filter to select **year 2024**, and look at the **Revenue by Territory** chart.

**Question to Answer:** "Looking at the year 2024, which are the top 3 sales territories by revenue, and what is the approximate revenue of each?"',
        'data_retrieval', 'Sales', 'easy',
        FALSE
    );

    -- ==========================================================================
    -- TASK 2: REVENUE TREND VISUALIZATION (INTERMEDIATE)
    -- ==========================================================================
    -- Difficulty: Intermediate - Requires viewing chart + filtering data
    -- Domain: Sales
    -- Expected Time: 5-8 minutes

    INSERT INTO public.experiment_tasks (
        id, experiment_id, participant_id, task_id, task_number,
        task_description, task_type, domain, complexity_level,
        is_tutorial
    ) VALUES (
        gen_random_uuid()::text, p_experiment_id, p_participant_id,
        'TASK_02', 2,
        '**Role:** Sales Analyst at AdventureWorks

**Scenario:** Your manager wants to understand seasonal sales patterns for 2023. They need to know which month performed best so the team can plan next year''s marketing budget around peak periods.

**Tip:** Go to the **Sales & Revenue** dashboard, use the **Time Range** filter to select **year 2023**, and look at the **Monthly Revenue Trend** chart.

**Question to Answer:** "Which month had the highest revenue in year 2023?"',
        'data_retrieval', 'Sales', 'easy',
        FALSE
    );

    -- ==========================================================================
    -- TASK 3: PROFITABILITY ANALYSIS (DIFFICULT)
    -- ==========================================================================
    -- Difficulty: Difficult - Requires cross-referencing multiple charts
    -- Domain: Production
    -- Expected Time: 8-12 minutes

    INSERT INTO public.experiment_tasks (
        id, experiment_id, participant_id, task_id, task_number,
        task_description, task_type, domain, complexity_level,
        is_tutorial
    ) VALUES (
        gen_random_uuid()::text, p_experiment_id, p_participant_id,
        'TASK_03', 3,
        '**Role:** Production Analyst at AdventureWorks

**Scenario:** Your team is reviewing product categories to understand the balance between inventory size and profitability. Management wants to know which category dominates in product count and how profitable that category actually is.

**Tip:** Go to the **Production & Inventory** dashboard. First, check the **Inventory by Category** chart to find the category with the most products. Then, look at the **Profit Margin by Category** table below the margin chart to find the average profit margin for that category.

**Question to Answer:** "Which product category has the largest number of products, and what is its average profit margin?"',
        'cross_reference', 'Production', 'moderate',
        FALSE
    );

    -- ==========================================================================
    -- TASK 4: SALES DEPARTMENT ROI ANALYSIS (DIFFICULT)
    -- ==========================================================================
    -- Difficulty: Difficult - Requires navigating 2 dashboards + manual calculation
    -- Domain: Sales + Operations
    -- Expected Time: 8-12 minutes

    INSERT INTO public.experiment_tasks (
        id, experiment_id, participant_id, task_id, task_number,
        task_description, task_type, domain, complexity_level,
        is_tutorial
    ) VALUES (
        gen_random_uuid()::text, p_experiment_id, p_participant_id,
        'TASK_04', 4,
        '**Role:** Business Analyst at AdventureWorks

**Scenario:** The CFO wants to evaluate the return on investment of the Sales department. They need to understand how many people work in Sales, what they earn, how much revenue they generated in 2024, and ultimately how much revenue each sales employee brings in on average. This will inform hiring decisions for the next fiscal year.

**Tip:** This task requires **two dashboards**:
1. Go to **Workforce & Operations** → find the **Sales** department in the **Department Details** table to get the employee count and average salary
2. Go to **Sales & Revenue** → check the **Total Revenue** KPI card (make sure the time range is set to **2024**)
3. Divide the total revenue by the number of Sales employees to get the revenue per employee

**Question to Answer:** "The Sales department is responsible for generating the company''s revenue. How many employees work in the Sales department, what is their average annual salary, and what was the total revenue generated in 2024? Based on these numbers, approximately how much revenue did each sales employee generate on average?"',
        'cross_reference', 'Sales + Operations', 'difficult',
        FALSE
    );

    -- ==========================================================================
    -- TASK 5: CROSS-DASHBOARD BUSINESS ANALYSIS (VERY DIFFICULT)
    -- ==========================================================================
    -- Difficulty: Very Difficult - Requires navigating 3 dashboards and connecting data
    -- Domain: Sales + Production + Operations
    -- Expected Time: 12-18 minutes

    INSERT INTO public.experiment_tasks (
        id, experiment_id, participant_id, task_id, task_number,
        task_description, task_type, domain, complexity_level,
        is_tutorial
    ) VALUES (
        gen_random_uuid()::text, p_experiment_id, p_participant_id,
        'TASK_05', 5,
        '**Role:** Business Intelligence Analyst at AdventureWorks

**Scenario:** The CEO has requested a comprehensive analysis of the company''s top-performing product category. They want to understand the full picture: how much revenue it drives, how profitable it is, and what the workforce behind it looks like. This cross-functional insight will be presented at the next board meeting to inform investment and hiring decisions.

**Tip:** This task requires navigating **all three dashboards**:
1. Go to **Sales & Revenue** → check the **Revenue by Product Category** chart to find the top category and its revenue percentage
2. Go to **Production & Inventory** → check the **Profit Margin by Category** table to find the average profit margin for that category
3. Go to **Workforce & Operations** → check the **Department Details** table to find the employee count and average salary for the department that manufactures these products

**Question to Answer:** "Which product category generates the highest revenue and what percentage of total revenue does it represent? What is the average profit margin for that category? How many employees work in the department that produces these products, and what is their average salary?"',
        'cross_reference', 'Multi-Domain', 'very_difficult',
        FALSE
    );

    RETURN 6;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- USAGE EXAMPLES
-- ============================================================================

-- 1. Assign tasks to a specific participant:
--    SELECT assign_6_experiment_tasks('default-experiment-001', 'participant-id-here');

-- 2. Assign tasks to ALL participants who don''t have tasks yet:
/*
DO $$
DECLARE
    participant_record RECORD;
    experiment_id VARCHAR(36) := 'default-experiment-001';
BEGIN
    FOR participant_record IN
        SELECT DISTINCT p.id
        FROM public.experiment_participants p
        LEFT JOIN public.experiment_tasks t ON p.id = t.participant_id
        WHERE t.id IS NULL
          AND p.experiment_id = experiment_id
    LOOP
        PERFORM assign_6_experiment_tasks(experiment_id, participant_record.id);
        RAISE NOTICE 'Assigned 6 tasks (1 tutorial + 5 real) to participant %', participant_record.id;
    END LOOP;
END $$;
*/

-- 3. Update existing participants with new task structure:
/*
-- First, delete old tasks
DELETE FROM public.experiment_tasks WHERE participant_id = 'YOUR-PARTICIPANT-ID';

-- Then assign new 6-task structure
SELECT assign_6_experiment_tasks('default-experiment-001', 'YOUR-PARTICIPANT-ID');
*/

-- ============================================================================
-- VERIFY TASKS
-- ============================================================================

-- View all tasks with tutorial status
SELECT
    t.task_number,
    t.task_id,
    t.is_tutorial,
    t.domain,
    t.complexity_level,
    LEFT(t.task_description, 60) as description_preview,
    p.participant_code
FROM public.experiment_tasks t
JOIN public.experiment_participants p ON t.participant_id = p.id
ORDER BY p.participant_code, t.task_number;

-- Count tasks per participant
SELECT
    p.participant_code,
    COUNT(t.id) as total_tasks,
    SUM(CASE WHEN t.is_tutorial THEN 1 ELSE 0 END) as tutorial_tasks,
    SUM(CASE WHEN NOT t.is_tutorial THEN 1 ELSE 0 END) as real_tasks
FROM public.experiment_participants p
LEFT JOIN public.experiment_tasks t ON p.id = t.participant_id
GROUP BY p.id, p.participant_code
ORDER BY p.participant_code;

-- ============================================================================
-- TASK SUMMARY
-- ============================================================================
-- Task 0: TUTORIAL - Inventory Risk Assessment (Tutorial) - Production
--         Purpose: Familiarize participants with system interface
--         Analysis: EXCLUDED from performance metrics
--
-- Task 1: Sales Territory Performance (Easy) - Sales
--         Top 3 territories by revenue in 2024
--         Expected: >90% control group success
--
-- Task 2: Revenue Trend Visualization (Intermediate) - Sales
--         Expected: ~70-80% control group success
--
-- Task 3: Profitability Analysis (Difficult) - Production
--         Expected: ~50-60% control group success
--
-- Task 4: Sales Department ROI (Difficult) - Sales + Operations
--         Cross-dashboard: employee count + salary + total revenue + calculation
--         Expected: ~30-40% control group success
--
-- Task 5: Revenue Concentration Analysis (Very Difficult) - Sales
--         Expected: ~20-30% control group success
-- ============================================================================
