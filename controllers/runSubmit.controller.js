const redisClient = require('../config/redisClient.js');
const { promisify } = require('util');
const { v4: uuidv4 } = require('uuid');
const { Submission } = require('../models/submission.model.js');
const { validationResult } = require('express-validator');

// Promisify Redis `lpush` for enqueuing submission data
const lpushAsync = promisify(redisClient.lpush).bind(redisClient);

const runSubmitProblem = async (req, res) => {
    // Step 1: Validate request
    const errors = validationResult(req);
    if (!errors.isEmpty()) {
        return res.status(400).json({ errors: errors.array() });
    }

    const { problemId, code, language, action } = req.body;
    let submission = null;

    try {
        const userId = req.session?.user?.id || null;

        // XCreate an entry in the database
        submission = await Submission.create({
            problem_id: problemId,
            user_id: userId,
            code,
            language,
            status: 'pending',
            action,
            createdAt: new Date(),
            updatedAt: new Date(),
        });

        console.log(`Submission stored with submissionId: ${submission.submission_id}, action: ${action}`);

        // Prepare submission data for Redis queue
        const submissionData = {
            submissionId: submission.submission_id,
            problemId,
            code,
            language,
            action,  // 'RUN' or 'SUBMIT'
            timestamp: new Date().toISOString(),
        };

        // Push submission data to the appropriate Redis queue
        const queue = action === 'RUN' ? 'runQueue' : 'submitQueue';
        await lpushAsync(queue, JSON.stringify(submissionData));
        console.log(`Submission enqueued with requestId: ${requestId} to ${queue}`);

        // Respond immediately to the frontend
        res.status(200).json({
            message: `${action} request enqueued successfully.`,
            submissionId: submission.submission_id,
        });
    }
    catch(error) {
        console.error(`Error processing ${action} request:`, error);
        res.status(500).json({ error: `Failed to ${action.toLowerCase()} the code.` });
    }
};

module.exports = { runSubmitProblem };
