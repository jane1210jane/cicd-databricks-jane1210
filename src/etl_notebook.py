# Databricks notebook source
# This file runs as a Databricks notebook on serverless compute.

import sys

# Serverless does not guarantee the current working directory.
# The bundle supplies the deployed absolute path, so imports do not rely on it.
dbutils.widgets.text("source_dir", "")
source_dir = dbutils.widgets.get("source_dir")
if not source_dir:
    raise ValueError("Run this notebook through the bundle Job with source_dir set")
sys.path.insert(0, source_dir)

from transforms import summarize_sales

# COMMAND ----------

dbutils.widgets.text("catalog", "workspace")
catalog = dbutils.widgets.get("catalog").strip()
if not catalog:
    raise ValueError("catalog must name an existing writable catalog")

# Quote the catalog as one SQL identifier, including embedded backticks.
quoted_catalog = "`" + catalog.replace("`", "``") + "`"
namespace = f"{quoted_catalog}.`github_cicd_demo`"
table_name = f"{namespace}.`sales_summary`"

# Only this dedicated demo schema/table is created or overwritten.
spark.sql(f"CREATE SCHEMA IF NOT EXISTS {namespace}")

# COMMAND ----------

sales = [("apple", 2, 120), ("banana", 3, 80), ("apple", 1, 120)]
summary = summarize_sales(sales)
result = spark.createDataFrame(summary, "product STRING, total_yen BIGINT")
result.write.format("delta").mode("overwrite").saveAsTable(table_name)

# COMMAND ----------

# Read the persisted table back: a failed check makes the Job and CI/CD fail.
saved = spark.table(table_name).orderBy("product")
actual = [(row.product, row.total_yen) for row in saved.collect()]
expected = [("apple", 360), ("banana", 240)]
if actual != expected:
    raise AssertionError(f"Unexpected table contents: {actual!r}")

display(saved)
print(f"SUCCESS: verified {table_name}")
