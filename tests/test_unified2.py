# Copyright (c) 2013 Jason Ish
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
# 1. Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright
#    notice, this list of conditions and the following disclaimer in the
#    documentation and/or other materials provided with the distribution.
#
# THIS SOFTWARE IS PROVIDED ``AS IS'' AND ANY EXPRESS OR IMPLIED
# WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR ANY DIRECT,
# INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
# HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT,
# STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING
# IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

from __future__ import print_function

import sys
import os.path
import shutil
import tempfile
import io
import logging

try:
    import unittest2 as unittest
except:
    import unittest

from idstools import unified2

logging.basicConfig(level=logging.DEBUG)

LOG = logging.getLogger(__name__)

class TestReadRecord(unittest.TestCase):

    # A unified2 test file containing 1 event consisting of 17 records.
    test_filename = "tests/multi-record-event.log"

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="idstools-test.")

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_growing_file(self):

        write_fileobj = open("%s/unified2.log" % self.tmpdir, "ab")
        write_fileobj.write(open(self.test_filename, "rb").read())
        write_fileobj.flush()
        write_fileobj.close()

        read_fileobj = open("%s/unified2.log" % self.tmpdir, "rb")

        for i in range(17):
            record = unified2.read_record(read_fileobj)
            self.assertTrue(record is not None, "record None at i=%d" % (i))
        self.assertTrue(unified2.read_record(read_fileobj) is None)

        # Grow the file by 17 more records.
        write_fileobj = open("%s/unified2.log" % self.tmpdir, "ab")
        write_fileobj.write(open(self.test_filename, "rb").read())
        write_fileobj.flush()
        write_fileobj.close()

        for i in range(17):
            record = unified2.read_record(read_fileobj)
            self.assertTrue(
                record is not None, 
                "record None at i=%d; expected on OSX w/Py2" % (i))
        self.assertTrue(unified2.read_record(read_fileobj) is None)

        read_fileobj.close()

    def test_decoders(self):
        """Based on our knowledge of the test file, check that the
        records were decoded as expected.

        """
        fileobj = open(self.test_filename, "rb")

        record = unified2.read_record(fileobj)
        self.assertEqual("207.25.71.28", record["source-ip"])
        self.assertEqual("10.20.11.123", record["destination-ip"])

class TestRecordReader(unittest.TestCase):

    # A unified2 test file containing 1 event consisting of 17 records.
    test_filename = "tests/multi-record-event.log"

    def test_short_read_of_header(self):

        # Just read in 6 bytes of the header.
        buf = open(self.test_filename, "rb").read(6)
        self.assertEquals(len(buf), 6)

        fileobj = io.BytesIO(buf)
        self.assertEquals(fileobj.tell(), 0)
        reader = unified2.RecordReader(fileobj)
        self.assertRaises(EOFError, reader.next)
        self.assertEquals(fileobj.tell(), 0)
    
    def test_short_read_of_body(self):

        # Just read in 12, 8 for the header and some body.
        buf = open(self.test_filename, "rb").read(12)
        self.assertEquals(len(buf), 12)

        fileobj = io.BytesIO(buf)
        self.assertEquals(fileobj.tell(), 0)
        reader = unified2.RecordReader(fileobj)
        self.assertRaises(EOFError, reader.next)
        self.assertEquals(fileobj.tell(), 0)

    def test_eof(self):
        """Test that we get None on EOF."""

        reader = unified2.RecordReader(open(self.test_filename, "rb"))
        for i in range(17):
            record = reader.next()
            self.assertTrue(record)
        self.assertFalse(reader.next())

    def test_iteration(self):

        # Should get 17 records.
        reader = unified2.RecordReader(open(self.test_filename, "rb"))
        records = [r for r in reader]
        self.assertEquals(len(records), 17)

class FileRecordReaderTest(unittest.TestCase):

    # A unified2 test file containing 1 event consisting of 17 records.
    test_filename = "tests/multi-record-event.log"

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="idstools-test.")

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_single_file_iteration(self):
        reader = unified2.FileRecordReader(self.test_filename)
        records = list(reader)
        self.assertEquals(17, len(records))
        self.assertEquals(None, reader.next())

    def test_multi_file_iteration(self):
        reader = unified2.FileRecordReader(
            self.test_filename, self.test_filename)
        records = list(reader)
        self.assertEquals(34, len(records))
        self.assertEquals(None, reader.next())

    def test_growing_file(self):

        log_file = open("%s/unified2.log.0001" % (self.tmpdir), "ab")
        log_file.write(open(self.test_filename, "rb").read())
        log_file.close()

        reader = unified2.FileRecordReader("%s/unified2.log.0001" % self.tmpdir)

        for i in range(17):
            self.assertTrue(reader.next() is not None)
        self.assertTrue(reader.next() is None)

        log_file = open("%s/unified2.log.0001" % (self.tmpdir), "ab")
        log_file.write(open(self.test_filename, "rb").read())
        log_file.close()

        for i in range(17):
            self.assertTrue(reader.next() is not None)
        self.assertTrue(reader.next() is None)

class AggregatorTestCase(unittest.TestCase):

    # A unified2 test file containing 1 event consisting of 17 records.
    test_filename = "tests/multi-record-event.log"

    def test_aggregator(self):

        aggregator = unified2.Aggregator()

        # We should not get an event from the aggregator as we pass in
        # the records from the first event.
        reader = unified2.RecordReader(open(self.test_filename, "rb"))
        for record in reader:
            event = aggregator.add(record)
            self.assertEqual(None, event)

        # On the first add of the next event we should get an event.
        reader = unified2.RecordReader(open(self.test_filename, "rb"))
        event = aggregator.add(reader.next())
        self.assertTrue(event)
        self.assertTrue(isinstance(event, unified2.Event))

        # The next 16 records should get added without an event being
        # generated.
        for record in reader:
            self.assertEqual(None, aggregator.add(record))

        # Now flush.
        event = aggregator.flush()
        self.assertTrue(event)
        self.assertTrue(isinstance(event, unified2.Event))

    def test_interleaved(self):
        
        # First read in all records from a known multi-record event.
        records = []
        reader = unified2.RecordReader(open(self.test_filename, "rb"))
        for record in reader:
            records.append(record)
        self.assertEquals(len(records), 17)

        # Modify the event ID of the last record.
        records[16]["event-id"] = records[16]["event-id"] - 1

        # Add all 17 records to the aggregator.  Should only end up
        # with 16 as the last one will be thrown out due to an
        # event-id mismatch.
        aggregator = unified2.Aggregator()
        for record in records:
            aggregator.add(record)
        self.assertEquals(len(aggregator.queue), 16)
        
class FileEventReaderTestCase(unittest.TestCase):

    # A unified2 test file containing 1 event consisting of 17 records.
    test_filename = "tests/multi-record-event.log"

    def test(self):
        """ Basic test. """

        reader = unified2.FileEventReader(
            self.test_filename, self.test_filename)
        
        # On our first call to next we should get an event.
        self.assertTrue(isinstance(reader.next(), unified2.Event))

        # The second read should also return an event.
        self.assertTrue(isinstance(reader.next(), unified2.Event))

        # The third shouldn't return anything, as we should be EOF.
        self.assertEqual(None, reader.next())

    def test_iteration(self):
        """ Iteration test. """
        reader = unified2.FileEventReader(
            self.test_filename, self.test_filename)
        self.assertEquals(len(list(reader)), 2)

class SpoolRecordReaderTestCase(unittest.TestCase):

    test_filename = "tests/multi-record-event.log"

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="idstools-test.")

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_get_filenames(self):

        shutil.copy("tests/merged.log", "%s/unified2.log.0001" % (self.tmpdir))
        shutil.copy("tests/merged.log", "%s/unified2.log.0002" % (self.tmpdir))
        shutil.copy("tests/merged.log", "%s/unified2.log.0003" % (self.tmpdir))
        shutil.copy("tests/merged.log", "%s/unified2.log.0004" % (self.tmpdir))
        shutil.copy("tests/merged.log", "%s/asdf.log.0004" % (self.tmpdir))

        reader = unified2.SpoolRecordReader(self.tmpdir, "unified2")
        filenames = reader.get_filenames()
        self.assertEqual(len(filenames), 4)
        for filename in filenames:
            self.assertTrue(filename.startswith("unified2.log"))

    def test_open_next(self):

        reader = unified2.SpoolRecordReader(self.tmpdir, "unified2")
        self.assertEquals(None, reader.open_next())

        shutil.copy("tests/merged.log", "%s/unified2.log.0001" % (self.tmpdir))
        shutil.copy("tests/merged.log", "%s/unified2.log.0002" % (self.tmpdir))
        shutil.copy("tests/merged.log", "%s/unified2.log.0003" % (self.tmpdir))
        shutil.copy("tests/merged.log", "%s/unified2.log.0004" % (self.tmpdir))

        next_filename = reader.open_next()
        self.assertEquals("unified2.log.0001", next_filename) 
        next_filename = reader.open_next()
        self.assertEquals("unified2.log.0002", next_filename) 
        next_filename = reader.open_next()
        self.assertEquals("unified2.log.0003", next_filename) 
        next_filename = reader.open_next()
        self.assertEquals("unified2.log.0004", next_filename) 

        next_filename = reader.open_next()
        self.assertEquals(None, next_filename)
        self.assertTrue(reader.fileobj is not None)

    def test_next(self):

        test_filename = "tests/multi-record-event.log"

        reader = unified2.SpoolRecordReader(self.tmpdir, "unified2")
        assert reader.next() is None

        # Copy in a file.
        shutil.copy(test_filename, "%s/unified2.log.1382627900" % self.tmpdir)

        # Should be able to get 17 records.
        for i in range(17):
            assert reader.next() is not None

        # The next record should be None.
        assert reader.next() is None

        # Copy in another file.
        shutil.copy(test_filename, "%s/unified2.log.1382627901" % self.tmpdir)

        # Should be able to get 17 records.
        for _ in range(17):
            assert reader.next() is not None

        # Copy in 2 more files, should be able to get 34 records
        # sequentially.
        shutil.copy(test_filename, "%s/unified2.log.1382627902" % self.tmpdir)
        shutil.copy(test_filename, "%s/unified2.log.1382627903" % self.tmpdir)
        for _ in range(17 * 2):
            assert reader.next() is not None

    def test_next_with_unpexted_eof(self):

        buf = io.BytesIO(open("tests/multi-record-event.log", "rb").read())

        reader = unified2.SpoolRecordReader(self.tmpdir, "unified2")

        # Write out a couple bytes and try to read.
        open("%s/unified2.log.0001" % self.tmpdir, "wb").write(buf.read(6))
        assert reader.next() is None

        # Write out the rest of file.
        open("%s/unified2.log.0001" % self.tmpdir, "ab").write(buf.read())
        assert reader.next() is not None

    def test_with_growing_file(self):

        reader = unified2.SpoolRecordReader(self.tmpdir, "unified2")

        log_file = open("%s/unified2.log.0001" % (self.tmpdir), "ab")
        log_file.write(open(self.test_filename, "rb").read())
        log_file.close()
        for i in range(17):
            self.assertTrue(reader.next() is not None)
        self.assertTrue(reader.next() is None)

        log_file = open("%s/unified2.log.0001" % (self.tmpdir), "ab")
        log_file.write(open(self.test_filename, "rb").read())
        log_file.close()
        for i in range(17):
            self.assertTrue(reader.next() is not None)
        self.assertTrue(reader.next() is None)

    def test_iteration(self):

        test_filename = "tests/multi-record-event.log"

        reader = unified2.SpoolRecordReader(self.tmpdir, "unified2")
        shutil.copy(test_filename, "%s/unified2.log.1382627902" % self.tmpdir)
        self.assertEquals(len(list(reader)), 17)

    def test_open_at_bookmark(self):

        # Create a spool directory with some files...
        shutil.copy(self.test_filename, "%s/unified2.log.0001" % (self.tmpdir))
        shutil.copy(self.test_filename, "%s/unified2.log.0002" % (self.tmpdir))

        # Make the 3rd one a concatenation of itself so we know a valid offset.
        open("%s/unified2.log.0003" % self.tmpdir, "ab").write(
            open(self.test_filename, "rb").read())
        open("%s/unified2.log.0003" % self.tmpdir, "ab").write(
            open(self.test_filename, "rb").read())

        # Now create the reader with a bookmark .
        reader = unified2.SpoolRecordReader(
            self.tmpdir, "unified2.log", "unified2.log.0003", 38950)

        # Now we should only read 17 records.
        self.assertEquals(len(list(reader)), 17)

class SpoolEventReaderTestCase(unittest.TestCase):

    test_filename = "tests/multi-record-event.log"

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp(prefix="idstools-test.")

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_eof(self):
        """ Basic test of the SpoolEventReader aggregrating spool reader. """

        reader = unified2.SpoolEventReader(self.tmpdir, "unified2")
        shutil.copy(
            self.test_filename, "%s/unified2.log.1382627900" % self.tmpdir)
        self.assertTrue(isinstance(reader.next(), unified2.Event))
        self.assertTrue(reader.next() is None)

    def rollover_hook(self, closed, opened):
        print("Closed: %s; Opened: %s." % (closed, opened))

    def test_with_growing_file(self):

        reader = unified2.SpoolEventReader(self.tmpdir, "unified2")

        log_file = open("%s/unified2.log.0001" % (self.tmpdir), "ab")
        log_file.write(open(self.test_filename, "rb").read())
        log_file.close()
        self.assertTrue(isinstance(reader.next(), unified2.Event))
        self.assertTrue(reader.next() is None)

        log_file = open("%s/unified2.log.0001" % (self.tmpdir), "ab")
        log_file.write(open(self.test_filename, "rb").read())
        log_file.close()
        self.assertTrue(isinstance(reader.next(), unified2.Event))
        self.assertTrue(reader.next() is None)

    def test_with_file_rotation(self):

        reader = unified2.SpoolEventReader(self.tmpdir, "unified2")

        for i in range(2):
            open("%s/unified2.log.%04d" % (self.tmpdir, i), "ab").write(
                open(self.test_filename, "rb").read())
            self.assertTrue(isinstance(reader.next(), unified2.Event))

        self.assertTrue(reader.next() is None)

    def test_bookmarking(self):
        """Test that when bookmarking is used, a second invocation of
        the SpoolEventReader picks up where it left off.

        """

        for i in range(2):
            open("%s/unified2.log.%04d" % (self.tmpdir, i), "ab").write(
                open(self.test_filename, "rb").read())

        reader = unified2.SpoolEventReader(
            self.tmpdir, "unified2", bookmark=True)

        event = reader.next()
        self.assertIsNotNone(event)
        print(reader.bookmark.get())
        bookmark_filename, bookmark_offset = reader.bookmark.get()
        self.assertEquals(bookmark_filename, "unified2.log.0000")

        # The offset should be the offset at end of the first event,
        # even though the offset of the underlying file has moved on.
        self.assertEquals(bookmark_offset, 38950)
        self.assertEquals(reader.reader.tell()[1], 68)

        # Now create a new SpoolEventReader, the underlying offset
        # should be our bookmark locations.
        reader = unified2.SpoolEventReader(
            self.tmpdir, "unified2", bookmark=True)
        bookmark_filename, bookmark_offset = reader.bookmark.get()
        underlying_filename, underlying_offset = reader.reader.tell()

        self.assertEquals(bookmark_filename, "unified2.log.0000")
        self.assertEquals(bookmark_offset, 38950)

        self.assertEquals(
            bookmark_filename, os.path.basename(underlying_filename))
        self.assertEquals(bookmark_offset, underlying_offset)

        # Read the next and final event, and check bookmark location.
        self.assertIsNotNone(reader.next())
        self.assertIsNone(reader.next())
        bookmark_filename, bookmark_offset = reader.bookmark.get()
        self.assertEquals(bookmark_filename, "unified2.log.0001")
        self.assertEquals(bookmark_offset, 38950)

        # As this was the last event, the underlying location should
        # be the same as the bookmark.
        bookmark_filename, bookmark_offset = reader.bookmark.get()
        underlying_filename, underlying_offset = reader.reader.tell()
        self.assertEquals(
            bookmark_filename, os.path.basename(underlying_filename))
        self.assertEquals(bookmark_offset, underlying_offset)
