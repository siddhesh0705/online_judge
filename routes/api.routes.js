const express = require('express');
const router = express.Router();
const { runSubmitProblem } = require('../controllers/runSubmit.controller.js');
const { register, login, logout } = require('../controllers/auth.controller.js');
const { body, validationResult } = require('express-validator');
const authMiddleware = require('../middlewares/auth.middleware.js');

// Registration Route
router.post('/register', register);

// Login Route
router.post('/login', login);

// Logout Route
router.post('/logout', logout); // Ensure user is authenticated before logging out

// Submit Problem Route (Ensure the user is authenticated)
router.post('/submit', runSubmitProblem);

// Update Submission Status Route (Ensure the user is authenticated)
//router.post('/update-status', authMiddleware, updateSubmissionStatus);

module.exports = router;
