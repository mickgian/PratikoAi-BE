import {
  validatePassword,
  validateEmail,
  getPasswordStrength,
  getPasswordStrengthLabel,
  getPasswordStrengthColor,
  type PasswordValidation,
  type EmailValidation,
} from '../validation';

describe('validatePassword', () => {
  describe('valid passwords', () => {
    test('accepts password with all requirements', () => {
      const result = validatePassword('Password123!');

      expect(result.isValid).toBe(true);
      expect(result.errors).toHaveLength(0);
      expect(result.checks).toEqual({
        length: true,
        uppercase: true,
        lowercase: true,
        number: true,
        specialChar: true,
      });
    });

    test('accepts password with minimum 8 characters', () => {
      const result = validatePassword('Pass12!@');

      expect(result.isValid).toBe(true);
      expect(result.errors).toHaveLength(0);
    });

    test('accepts password with various special characters', () => {
      const passwords = [
        'Password1!',
        'Password1@',
        'Password1#',
        'Password1$',
        'Password1%',
        'Password1^',
        'Password1&',
        'Password1*',
        'Password1(',
        'Password1)',
        'Password1,',
        'Password1.',
        'Password1?',
        'Password1"',
        'Password1:',
        'Password1{',
        'Password1}',
        'Password1|',
        'Password1<',
        'Password1>',
      ];

      passwords.forEach(password => {
        const result = validatePassword(password);
        expect(result.isValid).toBe(true);
        expect(result.checks.specialChar).toBe(true);
      });
    });

    test('accepts long password with all requirements', () => {
      const result = validatePassword('ThisIsAVeryLongPassword123!@#');

      expect(result.isValid).toBe(true);
      expect(result.errors).toHaveLength(0);
    });
  });

  describe('invalid passwords - length', () => {
    test('rejects password shorter than 8 characters', () => {
      const result = validatePassword('Pass1!');

      expect(result.isValid).toBe(false);
      expect(result.errors).toContain(
        'Password must be at least 8 characters long'
      );
      expect(result.checks.length).toBe(false);
    });

    test('rejects empty string', () => {
      const result = validatePassword('');

      expect(result.isValid).toBe(false);
      expect(result.errors).toContain(
        'Password must be at least 8 characters long'
      );
      expect(result.checks.length).toBe(false);
    });

    test('rejects password with exactly 7 characters', () => {
      const result = validatePassword('Pass1!A');

      expect(result.isValid).toBe(false);
      expect(result.errors).toContain(
        'Password must be at least 8 characters long'
      );
    });
  });

  describe('invalid passwords - missing uppercase', () => {
    test('rejects password without uppercase letter', () => {
      const result = validatePassword('password123!');

      expect(result.isValid).toBe(false);
      expect(result.errors).toContain(
        'Password must contain at least one uppercase letter'
      );
      expect(result.checks.uppercase).toBe(false);
    });

    test('rejects password with only numbers and special chars', () => {
      const result = validatePassword('12345678!@#$');

      expect(result.isValid).toBe(false);
      expect(result.errors).toContain(
        'Password must contain at least one uppercase letter'
      );
    });
  });

  describe('invalid passwords - missing lowercase', () => {
    test('rejects password without lowercase letter', () => {
      const result = validatePassword('PASSWORD123!');

      expect(result.isValid).toBe(false);
      expect(result.errors).toContain(
        'Password must contain at least one lowercase letter'
      );
      expect(result.checks.lowercase).toBe(false);
    });

    test('rejects uppercase only password', () => {
      const result = validatePassword('ABCDEFGH');

      expect(result.isValid).toBe(false);
      expect(result.checks.lowercase).toBe(false);
    });
  });

  describe('invalid passwords - missing number', () => {
    test('rejects password without number', () => {
      const result = validatePassword('Password!@#');

      expect(result.isValid).toBe(false);
      expect(result.errors).toContain(
        'Password must contain at least one number'
      );
      expect(result.checks.number).toBe(false);
    });

    test('rejects letters only password', () => {
      const result = validatePassword('Passwordonly');

      expect(result.isValid).toBe(false);
      expect(result.checks.number).toBe(false);
    });
  });

  describe('invalid passwords - missing special character', () => {
    test('rejects password without special character', () => {
      const result = validatePassword('Password123');

      expect(result.isValid).toBe(false);
      expect(result.errors).toContain(
        'Password must contain at least one special character'
      );
      expect(result.checks.specialChar).toBe(false);
    });

    test('rejects alphanumeric only password', () => {
      const result = validatePassword('Abc12345');

      expect(result.isValid).toBe(false);
      expect(result.checks.specialChar).toBe(false);
    });
  });

  describe('invalid passwords - multiple missing requirements', () => {
    test('rejects password missing all requirements', () => {
      const result = validatePassword('abc');

      expect(result.isValid).toBe(false);
      expect(result.errors).toHaveLength(4); // Has lowercase, missing 4 others
      expect(result.errors).toContain(
        'Password must be at least 8 characters long'
      );
      expect(result.errors).toContain(
        'Password must contain at least one uppercase letter'
      );
      expect(result.errors).toContain(
        'Password must contain at least one number'
      );
      expect(result.errors).toContain(
        'Password must contain at least one special character'
      );
    });

    test('rejects password missing multiple requirements', () => {
      const result = validatePassword('password');

      expect(result.isValid).toBe(false);
      expect(result.errors.length).toBeGreaterThan(1);
      expect(result.checks.uppercase).toBe(false);
      expect(result.checks.number).toBe(false);
      expect(result.checks.specialChar).toBe(false);
    });
  });

  describe('edge cases', () => {
    test('handles password with spaces', () => {
      const result = validatePassword('Pass word123!');

      expect(result.isValid).toBe(true);
      expect(result.checks.length).toBe(true);
    });

    test('handles password with unicode characters', () => {
      const result = validatePassword('Pässwörd123!');

      expect(result.isValid).toBe(true);
    });

    test('handles password with only special characters and numbers', () => {
      const result = validatePassword('!@#$1234');

      expect(result.isValid).toBe(false);
      expect(result.checks.uppercase).toBe(false);
      expect(result.checks.lowercase).toBe(false);
    });
  });
});

describe('validateEmail', () => {
  describe('valid emails', () => {
    test('accepts standard email format', () => {
      const result = validateEmail('user@example.com');

      expect(result.isValid).toBe(true);
      expect(result.error).toBeUndefined();
    });

    test('accepts email with plus sign', () => {
      const result = validateEmail('user+tag@example.com');

      expect(result.isValid).toBe(true);
      expect(result.error).toBeUndefined();
    });

    test('accepts email with dots', () => {
      const result = validateEmail('first.last@example.com');

      expect(result.isValid).toBe(true);
    });

    test('accepts email with numbers', () => {
      const result = validateEmail('user123@example456.com');

      expect(result.isValid).toBe(true);
    });

    test('accepts email with hyphens in domain', () => {
      const result = validateEmail('user@my-domain.com');

      expect(result.isValid).toBe(true);
    });

    test('accepts email with subdomain', () => {
      const result = validateEmail('user@mail.example.com');

      expect(result.isValid).toBe(true);
    });

    test('accepts email with underscore', () => {
      const result = validateEmail('user_name@example.com');

      expect(result.isValid).toBe(true);
    });

    test('accepts email with percentage', () => {
      const result = validateEmail('user%test@example.com');

      expect(result.isValid).toBe(true);
    });

    test('accepts email with long TLD', () => {
      const result = validateEmail('user@example.technology');

      expect(result.isValid).toBe(true);
    });
  });

  describe('invalid emails', () => {
    test('rejects empty string', () => {
      const result = validateEmail('');

      expect(result.isValid).toBe(false);
      expect(result.error).toBe('Email is required');
    });

    test('rejects email without @ symbol', () => {
      const result = validateEmail('userexample.com');

      expect(result.isValid).toBe(false);
      expect(result.error).toBe('Invalid email format');
    });

    test('rejects email without domain', () => {
      const result = validateEmail('user@');

      expect(result.isValid).toBe(false);
      expect(result.error).toBe('Invalid email format');
    });

    test('rejects email without local part', () => {
      const result = validateEmail('@example.com');

      expect(result.isValid).toBe(false);
      expect(result.error).toBe('Invalid email format');
    });

    test('rejects email without TLD', () => {
      const result = validateEmail('user@example');

      expect(result.isValid).toBe(false);
      expect(result.error).toBe('Invalid email format');
    });

    test('rejects email with spaces', () => {
      const result = validateEmail('user name@example.com');

      expect(result.isValid).toBe(false);
      expect(result.error).toBe('Invalid email format');
    });

    test('rejects email with multiple @ symbols', () => {
      const result = validateEmail('user@@example.com');

      expect(result.isValid).toBe(false);
      expect(result.error).toBe('Invalid email format');
    });

    test('rejects email with invalid characters', () => {
      const result = validateEmail('user<>@example.com');

      expect(result.isValid).toBe(false);
      expect(result.error).toBe('Invalid email format');
    });

    test('rejects email with single character TLD', () => {
      const result = validateEmail('user@example.c');

      expect(result.isValid).toBe(false);
      expect(result.error).toBe('Invalid email format');
    });

    test('accepts email starting with dot (per regex)', () => {
      // Current regex allows this - documenting actual behavior
      const result = validateEmail('.user@example.com');

      expect(result.isValid).toBe(true);
    });

    test('accepts email ending with dot before @ (per regex)', () => {
      // Current regex allows this - documenting actual behavior
      const result = validateEmail('user.@example.com');

      expect(result.isValid).toBe(true);
    });
  });

  describe('edge cases', () => {
    test('accepts email with consecutive dots (per regex)', () => {
      // Current regex allows this - documenting actual behavior
      const result = validateEmail('user..name@example.com');

      expect(result.isValid).toBe(true);
    });

    test('accepts email with capital letters', () => {
      const result = validateEmail('User@Example.COM');

      expect(result.isValid).toBe(true);
    });

    test('rejects just @ symbol', () => {
      const result = validateEmail('@');

      expect(result.isValid).toBe(false);
      expect(result.error).toBe('Invalid email format');
    });
  });
});

describe('getPasswordStrength', () => {
  test('returns 0 for empty password', () => {
    const strength = getPasswordStrength('');

    expect(strength).toBe(0);
  });

  test('returns 2 for password with only lowercase and length', () => {
    const strength = getPasswordStrength('abcdefgh');

    expect(strength).toBe(2); // length + lowercase
  });

  test('returns 3 for password with lowercase, uppercase, and length', () => {
    const strength = getPasswordStrength('Abcdefgh');

    expect(strength).toBe(3); // length + lowercase + uppercase
  });

  test('returns 4 for password with lowercase, uppercase, numbers, and length', () => {
    const strength = getPasswordStrength('Abcdefg1');

    expect(strength).toBe(4); // length + lowercase + uppercase + number
  });

  test('returns 4 for password missing one requirement', () => {
    const strength = getPasswordStrength('Abcdefg!');

    expect(strength).toBe(4);
  });

  test('returns 5 for password with all requirements', () => {
    const strength = getPasswordStrength('Password123!');

    expect(strength).toBe(5);
  });

  test('returns correct score for weak password', () => {
    const strength = getPasswordStrength('pass');

    expect(strength).toBe(1);
  });

  test('handles password with only special characters', () => {
    const strength = getPasswordStrength('!@#$%^&*');

    expect(strength).toBe(2); // length + special char
  });

  test('returns 1 for very short password with one characteristic', () => {
    const strength = getPasswordStrength('a');

    expect(strength).toBe(1); // only lowercase
  });

  test('handles password with mixed characteristics but short', () => {
    const strength = getPasswordStrength('Ab1!');

    expect(strength).toBe(4); // uppercase + lowercase + number + special (no length)
  });
});

describe('getPasswordStrengthLabel', () => {
  test('returns "Very Weak" for empty password', () => {
    const label = getPasswordStrengthLabel('');

    expect(label).toBe('Very Weak');
  });

  test('returns "Weak" for strength 1', () => {
    const label = getPasswordStrengthLabel('abc');

    expect(label).toBe('Weak'); // Has only lowercase (1 check)
  });

  test('returns "Fair" for strength 2', () => {
    const label = getPasswordStrengthLabel('abcdefgh');

    expect(label).toBe('Fair'); // Has length + lowercase (2 checks)
  });

  test('returns "Good" for strength 3', () => {
    const label = getPasswordStrengthLabel('Abcdefgh');

    expect(label).toBe('Good'); // Has length + lowercase + uppercase (3 checks)
  });

  test('returns "Strong" for strength 4', () => {
    const label = getPasswordStrengthLabel('Abcdefg1');

    expect(label).toBe('Strong'); // Has length + lowercase + uppercase + number (4 checks)
  });

  test('returns "Strong" for strength 4', () => {
    const label = getPasswordStrengthLabel('Abcdefg!'); // Missing number

    expect(label).toBe('Strong');
  });

  test('returns "Very Strong" for strength 5', () => {
    const label = getPasswordStrengthLabel('Password123!');

    expect(label).toBe('Very Strong');
  });

  test('handles short weak password', () => {
    const label = getPasswordStrengthLabel('a');

    expect(label).toBe('Weak'); // Has only lowercase (1 check)
  });

  test('handles password with only numbers', () => {
    const label = getPasswordStrengthLabel('12345678');

    expect(label).toBe('Fair');
  });

  test('handles very long complex password', () => {
    const label = getPasswordStrengthLabel(
      'ThisIsAVeryLongAndComplexPassword123!@#$%^&*()'
    );

    expect(label).toBe('Very Strong');
  });
});

describe('getPasswordStrengthColor', () => {
  test('returns red for empty password', () => {
    const color = getPasswordStrengthColor('');

    expect(color).toBe('text-red-500');
  });

  test('returns red for strength 0', () => {
    const color = getPasswordStrengthColor('abc');

    expect(color).toBe('text-red-500');
  });

  test('returns orange for strength 2', () => {
    const color = getPasswordStrengthColor('abcdefgh');

    expect(color).toBe('text-orange-500'); // length + lowercase = 2
  });

  test('returns yellow for strength 3', () => {
    const color = getPasswordStrengthColor('Abcdefgh');

    expect(color).toBe('text-yellow-500'); // length + lowercase + uppercase = 3
  });

  test('returns blue for strength 4', () => {
    const color = getPasswordStrengthColor('Abcdefg1');

    expect(color).toBe('text-blue-500'); // length + lowercase + uppercase + number = 4
  });

  test('returns blue for strength 4', () => {
    const color = getPasswordStrengthColor('Abcdefg!');

    expect(color).toBe('text-blue-500');
  });

  test('returns green for strength 5', () => {
    const color = getPasswordStrengthColor('Password123!');

    expect(color).toBe('text-green-500');
  });

  test('handles weak password color', () => {
    const color = getPasswordStrengthColor('pass');

    expect(color).toBe('text-red-500');
  });

  test('handles strong password color', () => {
    const color = getPasswordStrengthColor('MyP@ssw0rd');

    expect(color).toBe('text-green-500');
  });

  test('returns correct color for strength 1', () => {
    const color = getPasswordStrengthColor('a');

    expect(color).toBe('text-red-500'); // strength 1
  });
});

describe('Type definitions', () => {
  test('PasswordValidation interface has correct structure', () => {
    const validation: PasswordValidation = {
      isValid: true,
      errors: [],
      checks: {
        length: true,
        uppercase: true,
        lowercase: true,
        number: true,
        specialChar: true,
      },
    };

    expect(validation).toBeDefined();
    expect(typeof validation.isValid).toBe('boolean');
    expect(Array.isArray(validation.errors)).toBe(true);
    expect(typeof validation.checks).toBe('object');
  });

  test('EmailValidation interface has correct structure', () => {
    const validation: EmailValidation = {
      isValid: true,
      error: undefined,
    };

    expect(validation).toBeDefined();
    expect(typeof validation.isValid).toBe('boolean');
  });

  test('EmailValidation with error has correct structure', () => {
    const validation: EmailValidation = {
      isValid: false,
      error: 'Invalid email format',
    };

    expect(validation).toBeDefined();
    expect(typeof validation.isValid).toBe('boolean');
    expect(typeof validation.error).toBe('string');
  });
});
