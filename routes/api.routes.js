const express = require('express');
const router = express.Router();
const { submitProblem, updateSubmissionStatus } = require('../controllers/runSubmit.controller.js');
const { registerUser, loginUser, logoutUser } = require('../controllers/auth.controller.js');
const { body } = require('express-validator');
const authMiddleware = require('../middleware/auth.middleware.js');

router.post('/register', [
    body('email').isEmail().withMessage('Please provide a valid email.'),
    body('password').isLength({ min: 6 }).withMessage('Password must be at least 6 characters long.'),
], registerUser);

router.post('/login', [
    body('email').isEmail().withMessage('Please provide a valid email.'),
    body('password').exists().withMessage('Password is required.'),
], loginUser);

router.post('/logout', logoutUser);

router.post('/submit', authMiddleware, submitProblem);

router.post('/update-status', authMiddleware, updateSubmissionStatus);

module.exports = router;
