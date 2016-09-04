#!/usr/bin/env python
import os
import sys
import os.path as op
path = op.dirname(op.dirname(op.realpath(__file__)))
print (path)
sys.path.append(path)

from src.server.server import MMServer
from src.server.websocket_server import WebSocketServer
from SimpleWebSocketServer import SimpleWebSocketServer, WebSocket

from subprocess import Popen
import argparse
from src.game.game import Game
import time

import src.misc_constants as miscConstants
import src.game.game_constants as gameConstants

FNULL = open(os.devnull, 'w')

parameters = None
client_list = list()

def launch_clients():
    if parameters.client:
        numberOfClients = len(parameters.client)
        for client in parameters.client:
            launch_client(os.path.join(os.path.dirname(os.path.realpath(__file__)), os.pardir, 'test-clients/', client))
    else:
        numberOfClients = 0
    for x in xrange(numberOfClients, parameters.teams):
        launch_client(os.path.join(os.getcwd(), parameters.defaultClient))


def launch_client(client, port=None):
    c = Client_program(client, port)
    client_list.append(c)
    c.run()


def launch_client_test_game(client, port):
    launch_client(os.path.join(os.path.dirname(os.path.realpath(__file__)), os.pardir, client), port)
    launch_client(os.path.join(os.getcwd(), parameters.defaultClient), port)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Launch the server with p clients which "
        + "connect to it.")
    parser.add_argument(
        "-u", "--port",
        help="Specify the port the server runs on. " +
        "Default: {0}".format(miscConstants.port),
        default=miscConstants.port,
        type=int)
    parser.add_argument(
        "-w", "--debug-view",
        help="Run the debug view.",
        const=True,
        default=False,
        action="store_const",
    )
    parser.add_argument(
        "-l", "--log",
        help="Specify where the game log will be written to. " +
        "For example, ./gamerunner.py --log LOG.out. Default: {0}".
        format(miscConstants.logFile),
        default=miscConstants.logFile)
    parser.add_argument(
        "-t", "--teams",
        help="Specifies the number of teams. Default: {0}."
        .format(gameConstants.numPlayers),
        default=gameConstants.numPlayers,
        type=int)
    parser.add_argument(
        "-c", "--client",
        help="Specifies one or more clients to run. " +
        "Example: ./gamerunner.py -p 3 -c myClient -c python " +
        "The gamerunner will run a number of default clients (location optionally"
        "specified with -d) equal to players - specified clients",
        action="append")
    parser.add_argument(
        "-d", "--defaultClient",
        help="The default client to use when others aren't specified."
        "Default: {0}".format(miscConstants.defaultClient),
        default=os.path.join(*miscConstants.defaultClient.split("/")))

    parser.add_argument(
        "-v", "--verbose",
        help="Print player 1's standard output.",
        const=None,
        default=FNULL,
        action="store_const")
    parser.add_argument(
        "-vv", "--veryVerbose",
        help="Prints all players' standard output.",
        const=None,
        default=FNULL,
        action="store_const")

    parser.add_argument(
        "-o", "--only_log",
        help="Don't run the game, just use the log file for turns",
        const=True,
        default=False,
        action="store_const")
    parser.add_argument(
        "-th", "--turnsinhour",
        help="Set the game's length.",
        default=400,
        type=int)

    args = parser.parse_args()
    if args.teams < 2:
        sys.stdout.write(parser.format_usage())
        print ("{0}: error: Cannot run with less than two players".format(
            parser.prog))
        exit(1)
    if args.client and len(args.client) > args.teams:
        sys.stdout.write(parser.format_usage())
        print ("{0}: error: More clients specified than players".format(
            parser.prog))
        exit(1)
    return args


# A simple logger that writes things to a file and, if enabled, to the visualizer
class Logger(object):

    def __init__(self, fileName):
        # Logs
        self.file = fileName
        self.file_lines = []

        # WebSocket Instance
        self.serverInstance = WebSocketServer

        # WebSocket Server
        self.server = SimpleWebSocketServer('', 8080, self.serverInstance)
        self.server.serveforever()

        # self.serverInstance.init(fileName)

    # The function that logs will be sent to
    # @param stuff
    #   The stuff to be printed
    def print_stuff(self, json):
        self.file_lines.append(json)

        print("Turn " + str(len(self.file_lines)))

        if self.file is not None:
            with open(self.file, 'a') as f:
                f.write(json + '\n')

        self.serverInstance.broadCastMessage(json)

    def write_to_file(self):
        # write to log
        for line in self.file_lines:
            if self.file is not None:
                with open(self.file, 'a') as f:
                    f.write(line + '\n')


def main():
    global parameters
    parameters = parse_args()
    if parameters.only_log:
        fileLog = Logger(parameters.logJson)
        try:
            logJsonObject = []

            with open(parameters.log) as json_file:
                for line in json_file:
                    fileLog.print_stuff(line)
            if(logJsonObject is None):
                raise Exception
        except IOError:
            print("File " + parameters.logJson + " does not exist")
            raise
            exit(1)
        except Exception:
            print("Failed to parse log json data")
            raise
            exit(1)
    else:
        sys.stdout.write("Creating server with {0} players, ".format(
            parameters.teams))
        print ("Running server on port {0}\n".format(parameters.port))
        print ("Writing log to {0}".format(parameters.log))
        fileLog = Logger(parameters.log)
        print ("Starting Game")
        my_game = Game()
        serv = MMServer(parameters.teams,
                        my_game,
                        logger=fileLog)
        serv.run(parameters.port, launch_clients)
        with open(parameters.log, 'w'):
            pass
#        fileLog.write_to_file()

class Client_program(object):

    """
    This object holds and manages the processes for the
    connecting teams
    """
    first = True

    def __init__(self, client_path, port=None):
        """
        path of the client to run
        """
        self.client_path = client_path
        self.port = port

    def run(self):
        """
        """
        try:
            self.bot = Popen(["sh", os.path.join(self.client_path, "run.sh"),
                              "localhost", str(self.port or parameters.port)],
                             stdout=self.chose_output(), cwd=self.client_path)
        except OSError as e:
            msg = "the player {} failed to start with error {}".format(
                self.client_path, e)
            print (msg)
            raise ClientFailedToRun(msg)

    def kill(self):
        if not self.bot.poll():
            try:
                self.bot.kill()
            except OSError:
                pass

    def stop(self):
        try:
            self.bot.terminate()
        except OSError:
            pass

    @classmethod
    def chose_output(cls):
        output = parameters.veryVerbose
        if cls.first and parameters.veryVerbose == FNULL:
            output = parameters.verbose

        cls.first = False
        return output


class ClientFailedToRun(Exception):

    def __init__(self, msg):
        self.msg = msg

    def __str__(self):
        return self.msg


if __name__ == "__main__":
    main()
