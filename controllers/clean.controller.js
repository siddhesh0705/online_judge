const { Submission } = require('../models/submission.model');

const cleanupRunSubmissions = async(req, res) => {
    try {
        // Delete all 'RUN' entries that are not in 'pending'
        const deletedCount = await Submission.destroy({
            where: {
                action: 'RUN',
                status: {
                    [Submission.sequelize.Op.ne]: 'pending',
                },
            },
        });

        console.log(`Deleted ${deletedCount} completed RUN submissions.`);
    } catch (error) {
        console.error('Error cleaning up completed RUN submissions:', error);
        res.status(500).json({ error: 'Failed to clean up RUN submissions.' });
    }
};

module.exports = { cleanupRunSubmissions };
