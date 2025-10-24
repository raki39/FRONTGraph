-- Script de inicialização do ClickHouse para testes
-- Este script cria tabelas e insere dados de exemplo para testar o AgentSQL

-- Criar database de teste
CREATE DATABASE IF NOT EXISTS test_db;

-- Usar o database de teste
USE test_db;

-- ========================================
-- TABELA 1: Vendas (Sales)
-- ========================================
CREATE TABLE IF NOT EXISTS sales (
    sale_id UInt32,
    product_name String,
    category String,
    quantity UInt16,
    price Decimal(10, 2),
    sale_date Date,
    customer_id UInt32,
    region String
) ENGINE = MergeTree()
ORDER BY (sale_date, sale_id);

-- Inserir dados de exemplo
INSERT INTO sales VALUES (1, 'Laptop', 'Electronics', 2, 1200.00, '2024-01-15', 101, 'North');
INSERT INTO sales VALUES (2, 'Mouse', 'Electronics', 5, 25.00, '2024-01-16', 102, 'South');
INSERT INTO sales VALUES (3, 'Keyboard', 'Electronics', 3, 75.00, '2024-01-17', 103, 'East');
INSERT INTO sales VALUES (4, 'Monitor', 'Electronics', 1, 350.00, '2024-01-18', 101, 'North');
INSERT INTO sales VALUES (5, 'Desk', 'Furniture', 2, 450.00, '2024-01-19', 104, 'West');
INSERT INTO sales VALUES (6, 'Chair', 'Furniture', 4, 200.00, '2024-01-20', 105, 'North');
INSERT INTO sales VALUES (7, 'Laptop', 'Electronics', 1, 1200.00, '2024-01-21', 106, 'South');
INSERT INTO sales VALUES (8, 'Headphones', 'Electronics', 10, 50.00, '2024-01-22', 107, 'East');
INSERT INTO sales VALUES (9, 'Webcam', 'Electronics', 3, 80.00, '2024-01-23', 108, 'West');
INSERT INTO sales VALUES (10, 'Desk Lamp', 'Furniture', 5, 35.00, '2024-01-24', 109, 'North');
INSERT INTO sales VALUES (11, 'Notebook', 'Stationery', 20, 5.00, '2024-01-25', 110, 'South');
INSERT INTO sales VALUES (12, 'Pen', 'Stationery', 50, 1.50, '2024-01-26', 111, 'East');
INSERT INTO sales VALUES (13, 'Monitor', 'Electronics', 2, 350.00, '2024-01-27', 112, 'West');
INSERT INTO sales VALUES (14, 'Mouse Pad', 'Electronics', 8, 15.00, '2024-01-28', 113, 'North');
INSERT INTO sales VALUES (15, 'USB Cable', 'Electronics', 15, 10.00, '2024-01-29', 114, 'South');

-- ========================================
-- TABELA 2: Clientes (Customers)
-- ========================================
CREATE TABLE IF NOT EXISTS customers (
    customer_id UInt32,
    name String,
    email String,
    registration_date Date,
    country String,
    total_purchases UInt32
) ENGINE = MergeTree()
ORDER BY customer_id;

-- Inserir dados de exemplo
INSERT INTO customers VALUES (101, 'John Doe', 'john@example.com', '2023-06-15', 'USA', 15);
INSERT INTO customers VALUES (102, 'Jane Smith', 'jane@example.com', '2023-07-20', 'Canada', 8);
INSERT INTO customers VALUES (103, 'Bob Johnson', 'bob@example.com', '2023-08-10', 'UK', 12);
INSERT INTO customers VALUES (104, 'Alice Brown', 'alice@example.com', '2023-09-05', 'Australia', 6);
INSERT INTO customers VALUES (105, 'Charlie Wilson', 'charlie@example.com', '2023-10-12', 'USA', 20);
INSERT INTO customers VALUES (106, 'Diana Martinez', 'diana@example.com', '2023-11-18', 'Spain', 9);
INSERT INTO customers VALUES (107, 'Eve Davis', 'eve@example.com', '2023-12-22', 'France', 11);
INSERT INTO customers VALUES (108, 'Frank Garcia', 'frank@example.com', '2024-01-05', 'Mexico', 7);
INSERT INTO customers VALUES (109, 'Grace Lee', 'grace@example.com', '2024-01-10', 'South Korea', 14);
INSERT INTO customers VALUES (110, 'Henry Taylor', 'henry@example.com', '2024-01-15', 'Germany', 5);

-- ========================================
-- TABELA 3: Logs de Eventos (Event Logs)
-- ========================================
CREATE TABLE IF NOT EXISTS event_logs (
    event_id UInt64,
    event_type String,
    user_id UInt32,
    timestamp DateTime,
    duration_ms UInt32,
    status String,
    error_message String
) ENGINE = MergeTree()
ORDER BY (timestamp, event_id);

-- Inserir dados de exemplo (simulando logs de aplicação)
INSERT INTO event_logs VALUES (1, 'login', 101, '2024-01-15 08:30:00', 150, 'success', '');
INSERT INTO event_logs VALUES (2, 'page_view', 101, '2024-01-15 08:30:15', 50, 'success', '');
INSERT INTO event_logs VALUES (3, 'api_call', 102, '2024-01-15 09:15:00', 250, 'success', '');
INSERT INTO event_logs VALUES (4, 'login', 103, '2024-01-15 10:00:00', 180, 'success', '');
INSERT INTO event_logs VALUES (5, 'api_call', 103, '2024-01-15 10:05:00', 3500, 'error', 'Timeout');
INSERT INTO event_logs VALUES (6, 'page_view', 104, '2024-01-15 11:20:00', 75, 'success', '');
INSERT INTO event_logs VALUES (7, 'api_call', 105, '2024-01-15 12:30:00', 200, 'success', '');
INSERT INTO event_logs VALUES (8, 'login', 106, '2024-01-15 13:45:00', 160, 'success', '');
INSERT INTO event_logs VALUES (9, 'api_call', 107, '2024-01-15 14:00:00', 5000, 'error', 'Connection refused');
INSERT INTO event_logs VALUES (10, 'page_view', 108, '2024-01-15 15:10:00', 60, 'success', '');

-- ========================================
-- TABELA 4: Métricas de Performance (Performance Metrics)
-- ========================================
CREATE TABLE IF NOT EXISTS performance_metrics (
    metric_id UInt64,
    service_name String,
    metric_name String,
    value Float64,
    timestamp DateTime,
    tags Array(String)
) ENGINE = MergeTree()
ORDER BY (timestamp, service_name);

-- Inserir dados de exemplo
INSERT INTO performance_metrics VALUES (1, 'api-gateway', 'response_time_ms', 45.5, '2024-01-15 08:00:00', ['env:prod', 'region:us-east']);
INSERT INTO performance_metrics VALUES (2, 'api-gateway', 'response_time_ms', 52.3, '2024-01-15 08:01:00', ['env:prod', 'region:us-east']);
INSERT INTO performance_metrics VALUES (3, 'database', 'query_time_ms', 120.8, '2024-01-15 08:00:00', ['env:prod', 'db:postgres']);
INSERT INTO performance_metrics VALUES (4, 'database', 'query_time_ms', 95.2, '2024-01-15 08:01:00', ['env:prod', 'db:postgres']);
INSERT INTO performance_metrics VALUES (5, 'cache', 'hit_rate', 0.85, '2024-01-15 08:00:00', ['env:prod', 'cache:redis']);
INSERT INTO performance_metrics VALUES (6, 'cache', 'hit_rate', 0.92, '2024-01-15 08:01:00', ['env:prod', 'cache:redis']);
INSERT INTO performance_metrics VALUES (7, 'api-gateway', 'response_time_ms', 150.0, '2024-01-15 08:02:00', ['env:prod', 'region:us-east']);
INSERT INTO performance_metrics VALUES (8, 'api-gateway', 'response_time_ms', 48.7, '2024-01-15 08:03:00', ['env:prod', 'region:us-east']);
INSERT INTO performance_metrics VALUES (9, 'database', 'query_time_ms', 200.5, '2024-01-15 08:02:00', ['env:prod', 'db:postgres']);
INSERT INTO performance_metrics VALUES (10, 'database', 'query_time_ms', 88.3, '2024-01-15 08:03:00', ['env:prod', 'db:postgres']);

-- ========================================
-- VIEWS ÚTEIS PARA TESTES
-- ========================================

-- View: Total de vendas por categoria
CREATE VIEW IF NOT EXISTS sales_by_category AS
SELECT 
    category,
    count() as total_sales,
    sum(quantity) as total_quantity,
    sum(price * quantity) as total_revenue
FROM sales
GROUP BY category;

-- View: Métricas de performance agregadas por minuto
CREATE VIEW IF NOT EXISTS performance_by_minute AS
SELECT 
    toStartOfMinute(timestamp) as minute,
    service_name,
    metric_name,
    avg(value) as avg_value,
    quantile(0.95)(value) as p95_value,
    max(value) as max_value
FROM performance_metrics
GROUP BY minute, service_name, metric_name;

-- ========================================
-- TABELA COM DADOS TEMPORAIS (Time Series)
-- ========================================
CREATE TABLE IF NOT EXISTS time_series_data (
    timestamp DateTime,
    sensor_id UInt16,
    temperature Float32,
    humidity Float32,
    pressure Float32
) ENGINE = MergeTree()
ORDER BY (sensor_id, timestamp);

-- Inserir dados de série temporal
INSERT INTO time_series_data 
SELECT 
    toDateTime('2024-01-15 00:00:00') + INTERVAL number MINUTE as timestamp,
    (number % 5) + 1 as sensor_id,
    20 + (rand() % 100) / 10.0 as temperature,
    40 + (rand() % 400) / 10.0 as humidity,
    1000 + (rand() % 200) / 10.0 as pressure
FROM numbers(1000);

-- ========================================
-- INFORMAÇÕES ÚTEIS
-- ========================================

-- Mostrar todas as tabelas criadas
-- SELECT name, engine FROM system.tables WHERE database = 'test_db';

-- Contar registros em cada tabela
-- SELECT 'sales' as table_name, count() as row_count FROM sales
-- UNION ALL
-- SELECT 'customers', count() FROM customers
-- UNION ALL
-- SELECT 'event_logs', count() FROM event_logs
-- UNION ALL
-- SELECT 'performance_metrics', count() FROM performance_metrics
-- UNION ALL
-- SELECT 'time_series_data', count() FROM time_series_data;

