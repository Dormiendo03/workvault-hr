-- WorkVault Database Schema for Supabase (PostgreSQL)

-- Users table
CREATE TABLE IF NOT EXISTS users (
    id BIGSERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL CHECK (role IN ('admin', 'hr', 'employee')),
    department VARCHAR(100),
    salary DECIMAL(10, 2),
    leave_balance INTEGER DEFAULT 15,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Attendance table
CREATE TABLE IF NOT EXISTS attendance (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    date DATE NOT NULL,
    time_in TIME NOT NULL,
    time_out TIME,
    status VARCHAR(50) NOT NULL CHECK (status IN ('present', 'late', 'absent', 'on_leave')),
    face_verified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(user_id, date)
);

-- Leaves table
CREATE TABLE IF NOT EXISTS leaves (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    leave_type VARCHAR(50) NOT NULL CHECK (leave_type IN ('sick', 'vacation', 'personal', 'emergency')),
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    days_count INTEGER NOT NULL,
    reason TEXT NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'approved', 'rejected')),
    approved_by BIGINT REFERENCES users(id),
    approved_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Payroll table
CREATE TABLE IF NOT EXISTS payroll (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    period_start DATE NOT NULL,
    period_end DATE NOT NULL,
    base_salary DECIMAL(10, 2) NOT NULL,
    days_present INTEGER NOT NULL DEFAULT 0,
    days_absent INTEGER NOT NULL DEFAULT 0,
    days_on_leave INTEGER NOT NULL DEFAULT 0,
    deductions DECIMAL(10, 2) NOT NULL DEFAULT 0,
    net_salary DECIMAL(10, 2) NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'finalized', 'paid')),
    generated_by BIGINT REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for better performance
CREATE INDEX idx_attendance_user_date ON attendance(user_id, date);
CREATE INDEX idx_attendance_date ON attendance(date);
CREATE INDEX idx_leaves_user ON leaves(user_id);
CREATE INDEX idx_leaves_status ON leaves(status);
CREATE INDEX idx_payroll_user ON payroll(user_id);
CREATE INDEX idx_payroll_period ON payroll(period_start, period_end);
CREATE INDEX idx_users_role ON users(role);
CREATE INDEX idx_users_email ON users(email);

-- Create updated_at trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create trigger for users table
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Insert default admin user (password: admin123)
-- Note: Change this password immediately after first login!
INSERT INTO users (email, password_hash, name, role, is_active)
VALUES (
    'admin@workvault.com',
    'scrypt:32768:8:1$vQxZGZqKjXWLKqYu$c8f8e8c8f8e8c8f8e8c8f8e8c8f8e8c8f8e8c8f8e8c8f8e8c8f8e8c8f8e8c8f8e8c8f8e8c8f8e8c8f8e8c8f8',
    'System Administrator',
    'admin',
    TRUE
) ON CONFLICT (email) DO NOTHING;

-- Enable Row Level Security (RLS) - Optional but recommended
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE attendance ENABLE ROW LEVEL SECURITY;
ALTER TABLE leaves ENABLE ROW LEVEL SECURITY;
ALTER TABLE payroll ENABLE ROW LEVEL SECURITY;

-- Create RLS policies (adjust based on your security requirements)
-- These are basic policies - customize as needed

-- Users can read their own data
CREATE POLICY users_select_own ON users
    FOR SELECT USING (auth.uid()::text = id::text OR role IN ('admin', 'hr'));

-- Attendance policies
CREATE POLICY attendance_select ON attendance
    FOR SELECT USING (true);

CREATE POLICY attendance_insert ON attendance
    FOR INSERT WITH CHECK (true);

CREATE POLICY attendance_update ON attendance
    FOR UPDATE USING (true);

-- Leaves policies
CREATE POLICY leaves_select ON leaves
    FOR SELECT USING (true);

CREATE POLICY leaves_insert ON leaves
    FOR INSERT WITH CHECK (true);

CREATE POLICY leaves_update ON leaves
    FOR UPDATE USING (true);

-- Payroll policies
CREATE POLICY payroll_select ON payroll
    FOR SELECT USING (true);

CREATE POLICY payroll_insert ON payroll
    FOR INSERT WITH CHECK (true);

CREATE POLICY payroll_update ON payroll
    FOR UPDATE USING (true);
