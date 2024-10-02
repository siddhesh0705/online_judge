const { Submission } = require('../models/submission.model');

const pollSubmissionStatus = async (req, res) => {
    const { submissionId } = req.params;

    try {
        const submission = await Submission.findByPk(submissionId);

        if (!submission) {
            return res.status(404).json({ error: 'Submission not found' });
        }

        // Respond with the current status and output of the submission
        res.status(200).json({
            submissionId: submission.submission_id,
            status: submission.status,
            output: submission.output,
        });
    }
    catch(error) {
        console.error("Error fetching submission status:", error);
        res.status(500).json({ error: 'Failed to fetch submission status.' });
    }
};

module.exports = { pollSubmissionStatus };
