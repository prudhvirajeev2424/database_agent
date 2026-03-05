-- Table definitions
-- Database schema
CREATE DATABASE IF NOT EXISTS bank_db;
USE bank_db;

-- Customers Table
CREATE TABLE IF NOT EXISTS customers (
    customer_id INT PRIMARY KEY AUTO_INCREMENT,
    full_name VARCHAR(100),
    date_of_birth DATE,
    gender ENUM('MALE','FEMALE','OTHER'),
    email VARCHAR(100),
    phone VARCHAR(20),
    address VARCHAR(255),
    city VARCHAR(100),
    state VARCHAR(100),
    kyc_status ENUM('VERIFIED','PENDING'),
    risk_profile ENUM('LOW','MEDIUM','HIGH'),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Accounts Table
CREATE TABLE IF NOT EXISTS accounts (
    account_id INT PRIMARY KEY AUTO_INCREMENT,
    customer_id INT,
    account_number VARCHAR(20) UNIQUE,
    account_type ENUM('SAVINGS','CURRENT'),
    branch_name VARCHAR(100),
    balance DECIMAL(15,2),
    status ENUM('ACTIVE','BLOCKED'),
    opened_date DATE,
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
);

-- Transactions Table
CREATE TABLE IF NOT EXISTS transactions (
    transaction_id INT PRIMARY KEY AUTO_INCREMENT,
    account_id INT,
    transaction_reference VARCHAR(50),
    amount DECIMAL(15,2),
    transaction_type ENUM('DEPOSIT','WITHDRAWAL','TRANSFER'),
    transaction_mode ENUM('ONLINE','ATM','BRANCH'),
    transaction_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (account_id) REFERENCES accounts(account_id)
);

-- Loans Table
CREATE TABLE IF NOT EXISTS loans (
    loan_id INT PRIMARY KEY AUTO_INCREMENT,
    customer_id INT,
    loan_type ENUM('HOME','PERSONAL','CAR','BUSINESS'),
    loan_amount DECIMAL(15,2),
    interest_rate DECIMAL(5,2),
    loan_status ENUM('ACTIVE','CLOSED'),
    issued_date DATE,
    tenure_years INT,
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
);