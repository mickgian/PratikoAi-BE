/**
 * Frontend validation utilities to match backend requirements
 */

export interface PasswordValidation {
  isValid: boolean;
  errors: string[];
  checks: {
    length: boolean;
    uppercase: boolean;
    lowercase: boolean;
    number: boolean;
    specialChar: boolean;
  };
}

export interface EmailValidation {
  isValid: boolean;
  error?: string;
}

/**
 * Validate password strength according to backend requirements
 */
export function validatePassword(password: string): PasswordValidation {
  const checks = {
    length: password.length >= 8,
    uppercase: /[A-Z]/.test(password),
    lowercase: /[a-z]/.test(password),
    number: /[0-9]/.test(password),
    specialChar: /[!@#$%^&*(),.?":{}|<>]/.test(password),
  };

  const errors: string[] = [];
  
  if (!checks.length) {
    errors.push("Password must be at least 8 characters long");
  }
  if (!checks.uppercase) {
    errors.push("Password must contain at least one uppercase letter");
  }
  if (!checks.lowercase) {
    errors.push("Password must contain at least one lowercase letter");
  }
  if (!checks.number) {
    errors.push("Password must contain at least one number");
  }
  if (!checks.specialChar) {
    errors.push("Password must contain at least one special character");
  }

  return {
    isValid: Object.values(checks).every(Boolean),
    errors,
    checks,
  };
}

/**
 * Validate email format
 */
export function validateEmail(email: string): EmailValidation {
  const emailRegex = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;
  
  if (!email) {
    return { isValid: false, error: "Email is required" };
  }
  
  if (!emailRegex.test(email)) {
    return { isValid: false, error: "Invalid email format" };
  }

  return { isValid: true };
}

/**
 * Get password strength score (0-5)
 */
export function getPasswordStrength(password: string): number {
  const { checks } = validatePassword(password);
  return Object.values(checks).filter(Boolean).length;
}

/**
 * Get password strength label
 */
export function getPasswordStrengthLabel(password: string): string {
  const strength = getPasswordStrength(password);
  
  if (strength === 0) return "Very Weak";
  if (strength === 1) return "Weak";
  if (strength === 2) return "Fair";
  if (strength === 3) return "Good";
  if (strength === 4) return "Strong";
  return "Very Strong";
}

/**
 * Get password strength color for UI
 */
export function getPasswordStrengthColor(password: string): string {
  const strength = getPasswordStrength(password);
  
  if (strength <= 1) return "text-red-500";
  if (strength === 2) return "text-orange-500";
  if (strength === 3) return "text-yellow-500";
  if (strength === 4) return "text-blue-500";
  return "text-green-500";
}