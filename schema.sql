CREATE DATABASE IF NOT EXISTS joblens;
USE joblens;

CREATE TABLE IF NOT EXISTS users (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(100),
  email VARCHAR(150),
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS uploads (
  id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NULL,
  filename VARCHAR(255),
  file_text LONGTEXT,
  source VARCHAR(50), -- 'resume' or 'linkedin'
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS searches (
  id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NULL,
  query_text VARCHAR(500),
  keywords VARCHAR(255),
  location VARCHAR(100),
  results_count INT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
);
