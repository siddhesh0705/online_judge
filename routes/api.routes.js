const express = require('express');
const router = express.Router();
const submissionController = require('../controllers/submit.controller.js');

router.post('/submit',  submissionController.submitProblem);

module.exports = router;