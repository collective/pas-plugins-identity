"""What the token endpoint issues, and what it takes in exchange.

An authorization code, the access token it becomes, and the refresh token
rotated beside it. One package because they are one sequence: a code is
redeemed for a token pair, a refresh token is redeemed for the next pair, and
every rule about single use, rotation and replay is a rule about the seam
between two of them.
"""
