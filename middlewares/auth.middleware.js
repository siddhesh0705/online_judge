const authMiddleware = (req, res, next) => {
    if (req.session && req.session.user) {
        // User is authenticated
        next();
    } else {
        res.status(401).json({ error: 'Unauthorized. Please log in.' });
    }
};

module.exports = authMiddleware;
