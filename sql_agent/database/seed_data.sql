-- Sample data
-- Seed data
INSERT INTO customers 
(full_name, date_of_birth, gender, email, phone, address, city, state, kyc_status, risk_profile)
VALUES
('Arjun Mehta','1995-03-12','MALE','arjun.mehta@gmail.com','9876543210','12 MG Road','Chennai','Tamil Nadu','VERIFIED','LOW'),
('Priya Sharma','1992-07-25','FEMALE','priya.sharma@gmail.com','9876543211','45 Anna Nagar','Chennai','Tamil Nadu','VERIFIED','MEDIUM'),
('Rahul Verma','1988-11-18','MALE','rahul.verma@gmail.com','9876543212','78 T Nagar','Chennai','Tamil Nadu','PENDING','HIGH'),
('Sneha Iyer','1996-02-09','FEMALE','sneha.iyer@gmail.com','9876543213','23 Velachery','Chennai','Tamil Nadu','VERIFIED','LOW'),
('Vikram Reddy','1990-09-30','MALE','vikram.reddy@gmail.com','9876543214','56 Banjara Hills','Hyderabad','Telangana','VERIFIED','MEDIUM'),
('Ananya Gupta','1994-06-14','FEMALE','ananya.gupta@gmail.com','9876543215','19 Salt Lake','Kolkata','West Bengal','PENDING','LOW'),
('Rohan Das','1985-01-05','MALE','rohan.das@gmail.com','9876543216','44 Park Street','Kolkata','West Bengal','VERIFIED','HIGH'),
('Meera Nair','1993-08-22','FEMALE','meera.nair@gmail.com','9876543217','67 Marine Drive','Mumbai','Maharashtra','VERIFIED','MEDIUM'),
('Karan Singh','1991-04-11','MALE','karan.singh@gmail.com','9876543218','90 Andheri','Mumbai','Maharashtra','PENDING','LOW'),
('Pooja Patel','1997-12-03','FEMALE','pooja.patel@gmail.com','9876543219','34 Navrangpura','Ahmedabad','Gujarat','VERIFIED','LOW'),
('Amit Kumar','1987-05-19','MALE','amit.kumar@gmail.com','9876543220','11 Sector 62','Noida','UP','VERIFIED','MEDIUM'),
('Divya Rao','1998-10-27','FEMALE','divya.rao@gmail.com','9876543221','29 Whitefield','Bangalore','Karnataka','PENDING','LOW'),
('Suresh Pillai','1984-03-15','MALE','suresh.pillai@gmail.com','9876543222','52 Aluva','Kochi','Kerala','VERIFIED','HIGH'),
('Neha Jain','1999-07-07','FEMALE','neha.jain@gmail.com','9876543223','18 Malviya Nagar','Delhi','Delhi','VERIFIED','LOW'),
('Manoj Yadav','1989-09-21','MALE','manoj.yadav@gmail.com','9876543224','73 Gomti Nagar','Lucknow','UP','PENDING','MEDIUM');


INSERT INTO accounts
(customer_id, account_number, account_type, branch_name, balance, status, opened_date)
VALUES
(1,'ACC10001','SAVINGS','Chennai Main',75000.00,'ACTIVE','2022-01-10'),
(2,'ACC10002','CURRENT','Chennai Main',150000.00,'ACTIVE','2021-03-15'),
(3,'ACC10003','SAVINGS','Chennai T Nagar',25000.00,'BLOCKED','2023-02-20'),
(4,'ACC10004','SAVINGS','Chennai Velachery',98000.00,'ACTIVE','2020-07-11'),
(5,'ACC10005','CURRENT','Hyderabad Central',200000.00,'ACTIVE','2019-09-19'),
(6,'ACC10006','SAVINGS','Kolkata Salt Lake',45000.00,'ACTIVE','2022-11-05'),
(7,'ACC10007','CURRENT','Kolkata Park Street',175000.00,'ACTIVE','2021-06-30'),
(8,'ACC10008','SAVINGS','Mumbai Marine',62000.00,'ACTIVE','2023-01-25'),
(9,'ACC10009','SAVINGS','Mumbai Andheri',33000.00,'BLOCKED','2022-04-14'),
(10,'ACC10010','CURRENT','Ahmedabad Central',125000.00,'ACTIVE','2020-10-10'),
(11,'ACC10011','SAVINGS','Noida Sector 62',54000.00,'ACTIVE','2021-08-08'),
(12,'ACC10012','SAVINGS','Bangalore Whitefield',76000.00,'ACTIVE','2022-12-12'),
(13,'ACC10013','CURRENT','Kochi Aluva',210000.00,'ACTIVE','2018-05-22'),
(14,'ACC10014','SAVINGS','Delhi Malviya Nagar',48000.00,'ACTIVE','2023-03-03'),
(15,'ACC10015','SAVINGS','Lucknow Gomti Nagar',39000.00,'ACTIVE','2022-09-17');


INSERT INTO transactions
(account_id, transaction_reference, amount, transaction_type, transaction_mode)
VALUES
(1,'TXN001',5000.00,'DEPOSIT','ONLINE'),
(2,'TXN002',10000.00,'WITHDRAWAL','ATM'),
(3,'TXN003',2500.00,'DEPOSIT','BRANCH'),
(4,'TXN004',7000.00,'TRANSFER','ONLINE'),
(5,'TXN005',15000.00,'DEPOSIT','BRANCH'),
(6,'TXN006',3000.00,'WITHDRAWAL','ATM'),
(7,'TXN007',12000.00,'TRANSFER','ONLINE'),
(8,'TXN008',4500.00,'DEPOSIT','ONLINE'),
(9,'TXN009',2000.00,'WITHDRAWAL','ATM'),
(10,'TXN010',9000.00,'TRANSFER','ONLINE'),
(11,'TXN011',3500.00,'DEPOSIT','BRANCH'),
(12,'TXN012',6000.00,'WITHDRAWAL','ATM'),
(13,'TXN013',20000.00,'DEPOSIT','ONLINE'),
(14,'TXN014',1500.00,'WITHDRAWAL','ATM'),
(15,'TXN015',8000.00,'TRANSFER','BRANCH');


INSERT INTO loans
(customer_id, loan_type, loan_amount, interest_rate, loan_status, issued_date, tenure_years)
VALUES
(1,'HOME',2500000.00,8.50,'ACTIVE','2021-05-01',20),
(2,'PERSONAL',500000.00,12.00,'ACTIVE','2022-06-15',5),
(3,'CAR',800000.00,9.25,'CLOSED','2020-03-10',7),
(4,'HOME',3000000.00,8.75,'ACTIVE','2019-11-20',25),
(5,'BUSINESS',1500000.00,11.00,'ACTIVE','2021-01-01',10),
(6,'PERSONAL',400000.00,13.50,'CLOSED','2020-08-18',4),
(7,'CAR',900000.00,9.50,'ACTIVE','2022-09-09',6),
(8,'HOME',2200000.00,8.60,'ACTIVE','2023-02-14',20),
(9,'PERSONAL',300000.00,14.00,'ACTIVE','2023-03-01',3),
(10,'BUSINESS',2000000.00,10.75,'ACTIVE','2018-12-12',12),
(11,'CAR',750000.00,9.10,'CLOSED','2019-07-07',5),
(12,'PERSONAL',450000.00,12.75,'ACTIVE','2022-04-22',5),
(13,'HOME',3500000.00,8.40,'ACTIVE','2020-10-10',30),
(14,'CAR',650000.00,9.80,'ACTIVE','2023-01-01',5),
(15,'BUSINESS',1800000.00,11.50,'ACTIVE','2021-09-30',8);


